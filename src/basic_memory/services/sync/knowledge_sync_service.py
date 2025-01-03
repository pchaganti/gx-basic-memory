"""Service for managing entities in the database."""

from typing import Dict

from loguru import logger

from basic_memory.models import Entity as EntityModel, Observation, Relation
from basic_memory.markdown.schemas import EntityMarkdown
from basic_memory.schemas.request import ObservationCreate
from basic_memory.services import EntityService, ObservationService, RelationService


def entity_model_from_markdown(markdown: EntityMarkdown) -> EntityModel:
    """Convert markdown entity to model.

    Args:
        markdown: Parsed markdown entity
        include_relations: Whether to include relations. Set False for first sync pass.
    """
    model = EntityModel(
        name=markdown.content.title,
        entity_type=markdown.frontmatter.type,
        path_id=markdown.frontmatter.id,
        file_path=markdown.frontmatter.id,
        description=markdown.content.description,
        observations=[Observation(content=obs.content) for obs in markdown.content.observations],
    )
    return model


class KnowledgeSyncService:
    """Service for managing entities in the database."""

    def __init__(
        self,
        entity_service: EntityService,
        observation_service: ObservationService,
        relation_service: RelationService,
    ):
        self.entity_service = entity_service
        self.observation_service = observation_service
        self.relation_service = relation_service

    async def delete_entity(self, path_id: str) -> bool:
        return await self.entity_service.delete_entity(path_id)

    async def create_entity_and_observations(self, markdown: EntityMarkdown) -> EntityModel:
        """First pass: Create entity and observations only.

        Creates the entity with null checksum to indicate sync not complete.
        Relations will be added in second pass.
        """
        logger.debug(f"Creating entity without relations: {markdown.frontmatter.id}")
        model = entity_model_from_markdown(markdown)
        model.checksum = None  # Mark as incomplete sync
        return await self.entity_service.add(model)

    async def update_entity_and_observations(
        self, path_id: str, markdown: EntityMarkdown
    ) -> EntityModel:
        """First pass: Update entity fields and observations.

        Updates everything except relations and sets null checksum
        to indicate sync not complete.
        """
        logger.debug(f"Updating entity without relations: {path_id}")
        db_entity = await self.entity_service.get_by_path_id(path_id)

        # Update fields from markdown
        db_entity.name = markdown.content.title
        db_entity.entity_type = markdown.frontmatter.type
        db_entity.description = markdown.content.description

        # Clear and update observations
        await self.observation_service.delete_by_entity(db_entity.id)
        observations = [
            Observation(entity_id=db_entity.id,  
                        content=obs.content, 
                        category=obs.category,
                        context=obs.context) for obs in markdown.content.observations
        ]
        await self.observation_service.add_all(observations)

        # update entity
        # checksum value is None == not finished with sync
        return await self.entity_service.update_entity(
            db_entity.path_id,
            {
                "name": db_entity.name,
                "entity_type": db_entity.entity_type,
                "description": db_entity.description,
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
        db_entity = await self.entity_service.get_by_path_id(markdown.frontmatter.id)

        # get all entities from relations
        target_entity_path_ids = [rel.target for rel in markdown.content.relations]
        target_entities = await self.entity_service.open_nodes(target_entity_path_ids)

        # dict by path
        entity_by_path = {e.path_id: e for e in target_entities}

        # Clear and update relations
        await self.relation_service.delete_outgoing_relations_from_entity(db_entity.id)
        relations = [
            Relation(
                from_id=db_entity.id,
                to_id=entity_by_path[rel.target].id,
                relation_type=rel.type,
                context=rel.context,
            )
            for rel in markdown.content.relations
            if rel.target in entity_by_path  # Only create relations if target exists
        ]
        await self.relation_service.create_relations(relations)

        # Set final checksum to mark sync complete
        return await self.entity_service.update_entity(
            db_entity.path_id, {"checksum": checksum}
        )
