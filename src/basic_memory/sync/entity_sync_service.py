"""Service for managing entities in the database."""

from pathlib import Path

from loguru import logger
from sqlalchemy.exc import IntegrityError

from basic_memory.markdown.schemas import EntityMarkdown
from basic_memory.markdown.utils import entity_model_from_markdown
from basic_memory.models import Entity as EntityModel, Observation, Relation, ObservationCategory
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.link_resolver import LinkResolver
from basic_memory.utils import generate_permalink




class EntitySyncService:
    """Service for managing entities in the database."""

    def __init__(
        self,
        entity_repository: EntityRepository,
        observation_repository: ObservationRepository,
        relation_repository: RelationRepository,
        link_resolver: LinkResolver,
    ):
        self.entity_repository = entity_repository
        self.observation_repository = observation_repository
        self.relation_repository = relation_repository
        self.link_resolver = link_resolver

    async def delete_entity_by_file_path(self, file_path: str) -> bool:
        return await self.entity_repository.delete_by_file_path(file_path)

    async def create_entity_from_markdown(
        self, file_path: str, markdown: EntityMarkdown
    ) -> EntityModel:
        """First pass: Create entity and observations only.

        Creates the entity with null checksum to indicate sync not complete.
        Relations will be added in second pass.
        """
        logger.debug(f"Creating entity: {markdown.frontmatter.title}")
        model = entity_model_from_markdown(file_path, markdown)

        # Mark as incomplete sync
        model.checksum = None
        # Set timestamps from frontmatter
        created_at = markdown.frontmatter.created
        updated_at = markdown.frontmatter.modified

        model.created_at = created_at
        model.updated_at = updated_at

        for obs in model.observations:
            obs.created_at = created_at
            obs.updated_at = updated_at

        for rel in model.relations:
            rel.created_at = created_at
            rel.updated_at = updated_at

        return await self.entity_repository.add(model)

    async def update_entity_and_observations(
        self, file_path: str, markdown: EntityMarkdown
    ) -> EntityModel:
        """First pass: Update entity fields and observations.

        Updates everything except relations and sets null checksum
        to indicate sync not complete.
        """
        logger.debug(f"Updating entity and observations: {file_path}")
        db_entity = await self.entity_repository.get_by_file_path(file_path)
        if not db_entity:
            raise EntityNotFoundError(f"Entity not found: {file_path}")

        # Update fields from markdown
        db_entity.title = markdown.frontmatter.title
        db_entity.entity_type = markdown.frontmatter.type
        db_entity.summary = markdown.content

        # Clear observations for entity
        await self.observation_repository.delete_by_fields(entity_id=db_entity.id)

        # add new observations
        observations = [
            Observation(
                entity_id=db_entity.id,
                content=obs.content,
                category=obs.category,
                context=obs.context,
            )
            for obs in markdown.observations
        ]
        await self.observation_repository.add_all(observations)

        # update entity
        # checksum value is None == not finished with sync
        return await self.entity_repository.update(
            db_entity.id,
            {
                "title": db_entity.title,
                "entity_type": db_entity.entity_type,
                "summary": db_entity.summary,
                "created_at": markdown.frontmatter.created,
                "updated_at": markdown.frontmatter.modified,
                # Mark as incomplete
                "checksum": None,
            },
        )

    async def update_entity_relations(
        self,
        file_path: str,
        markdown: EntityMarkdown,
    ) -> EntityModel:
        """Update relations for entity"""
        logger.debug(f"Updating relations for entity: {file_path}")
        db_entity = await self.entity_repository.get_by_file_path(file_path)

        # Clear existing relations first
        await self.relation_repository.delete_outgoing_relations_from_entity(db_entity.id)

        # Process each relation
        for rel in markdown.relations:
            # Resolve the target permalink
            target_entity = await self.link_resolver.resolve_link(
                rel.target,
            )

            # if the target is found, store the id
            target_id = target_entity.id if target_entity else None
            # if the target is found, store the title, otherwise add the target for a "forward link"
            target_name = target_entity.title if target_entity else rel.target

            # Create the relation
            relation = Relation(
                from_id=db_entity.id,
                to_id=target_id,
                to_name=target_name,
                relation_type=rel.type,
                context=rel.context,
            )
            try:
                await self.relation_repository.add(relation)
            except IntegrityError:
                # Unique constraint violation - relation already exists
                logger.debug(
                    f"Skipping duplicate relation {rel.type} from {db_entity.permalink} target: {rel.target}, type: {rel.type}"
                )
                continue

        return await self.entity_repository.get_by_file_path(file_path)
