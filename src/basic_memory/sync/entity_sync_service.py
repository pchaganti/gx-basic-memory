"""Service for managing entities in the database."""

from loguru import logger

from basic_memory.models import Entity as EntityModel, Observation, Relation, ObservationCategory
from basic_memory.markdown.schemas import EntityMarkdown
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository
from basic_memory.services.exceptions import EntityNotFoundError


def entity_model_from_markdown(file_path: str, markdown: EntityMarkdown) -> EntityModel:
    """Convert markdown entity to model.

    Args:
        markdown: Parsed markdown entity
        include_relations: Whether to include relations. Set False for first sync pass.
    """

    # Validate/default category
    def get_valid_category(obs):
        if not obs.category or obs.category not in [c.value for c in ObservationCategory]:
            return ObservationCategory.NOTE.value
        return obs.category

    model = EntityModel(
        title=markdown.frontmatter.title,
        entity_type=markdown.frontmatter.type,
        path_id=markdown.frontmatter.id,
        file_path=file_path,
        content_type="text/markdown",
        summary=markdown.content.content,
        observations=[
            Observation(content=obs.content, category=get_valid_category(obs), context=obs.context)
            for obs in markdown.content.observations
        ],
    )
    return model


class EntitySyncService:
    """Service for managing entities in the database."""

    def __init__(
        self,
        entity_repository: EntityRepository,
        observation_repository: ObservationRepository,
        relation_repository: RelationRepository,
    ):
        self.entity_repository = entity_repository
        self.observation_repository = observation_repository
        self.relation_repository = relation_repository

    async def delete_entity_by_file_path(self, file_path: str) -> bool:
        return await self.entity_repository.delete_by_file_path(file_path)

    async def create_entity_from_markdown(
        self, file_path: str, markdown: EntityMarkdown
    ) -> EntityModel:
        """First pass: Create entity and observations only.

        Creates the entity with null checksum to indicate sync not complete.
        Relations will be added in second pass.
        """
        logger.debug(f"Creating entity without relations: {markdown.frontmatter.id}")
        model = entity_model_from_markdown(file_path, markdown)

        # Mark as incomplete sync
        model.checksum = None  
        return await self.entity_repository.add(model)

    async def update_entity_and_observations(
        self, path_id: str, markdown: EntityMarkdown
    ) -> EntityModel:
        """First pass: Update entity fields and observations.

        Updates everything except relations and sets null checksum
        to indicate sync not complete.
        """
        logger.debug(f"Updating entity and observations: {path_id}")
        db_entity = await self.entity_repository.get_by_path_id(path_id)
        if not db_entity:
            raise EntityNotFoundError(f"Entity not found: {path_id}")

        # Update fields from markdown
        db_entity.title = markdown.frontmatter.title
        db_entity.entity_type = markdown.frontmatter.type
        db_entity.summary = markdown.content.content

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
            for obs in markdown.content.observations
        ]
        await self.observation_repository.add_all(observations)

        # update entity
        # checksum value is None == not finished with sync
        return await self.entity_repository.update(
            db_entity.id,
            {
                "name": db_entity.title,
                "entity_type": db_entity.entity_type,
                "summary": db_entity.summary,
                # Mark as incomplete
                "checksum": None,
            },
        )

    async def update_entity_relations(self, markdown: EntityMarkdown, checksum: str) -> EntityModel:
        """Second pass: Update relations and set checksum.

        Args:
            markdown: Parsed markdown entity with relations
            checksum: Final checksum to set after relations are updated
        """
        logger.debug(f"Updating relations for entity: {markdown.frontmatter.id}")
        db_entity = await self.entity_repository.get_by_path_id(markdown.frontmatter.id)

        # get all entities from relations
        target_entity_path_ids = [rel.target for rel in markdown.content.relations]
        target_entities = await self.entity_repository.find_by_path_ids(target_entity_path_ids)

        # dict by path
        entity_by_path = {e.path_id: e for e in target_entities}

        # Clear and update relations
        await self.relation_repository.delete_outgoing_relations_from_entity(db_entity.id)

        # Use dict to deduplicate relations keyed by (target, type)
        relation_dict = {}
        for rel in markdown.content.relations:
            if rel.target not in entity_by_path:
                continue  # Skip if target doesn't exist

            to_id = entity_by_path[rel.target].id
            key = (to_id, rel.type)

            # Only keep the first instance of each relation type to a target
            if key not in relation_dict:
                relation_dict[key] = Relation(
                    from_id=db_entity.id,
                    to_id=to_id,
                    relation_type=rel.type,
                    context=rel.context,
                )
            else:
                logger.info(
                    f"Skipping duplicate relation '{rel.type}' to '{rel.target}' in {markdown.frontmatter.id}"
                )

        # Create unique relations
        await self.relation_repository.add_all(relation_dict.values())

        # Set final checksum to mark sync complete
        return await self.entity_repository.update(db_entity.id, {"checksum": checksum})
