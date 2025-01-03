"""Service for managing entities in the database."""
from typing import Dict

from loguru import logger

from basic_memory.models import Entity as EntityModel, Observation, Relation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.markdown.schemas import EntityMarkdown
from basic_memory.services import EntityService
from basic_memory.services.service import BaseService


def entity_model_from_markdown(
    markdown: EntityMarkdown
) -> EntityModel:
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


class EntitySyncService(EntityService):
    """Service for managing entities in the database."""

    def __init__(self, entity_repository: EntityRepository):
        super().__init__(entity_repository)

    async def create_entity_without_relations(self, markdown: EntityMarkdown) -> EntityModel:
        """First pass: Create entity and observations only.

        Creates the entity with null checksum to indicate sync not complete.
        Relations will be added in second pass.
        """
        logger.debug(f"Creating entity without relations: {markdown.frontmatter.id}")
        model = entity_model_from_markdown(markdown)
        model.checksum = None  # Mark as incomplete sync
        return await self.repository.add(model)

    async def update_entity_without_relations(
        self, path_id: str, markdown: EntityMarkdown
    ) -> EntityModel:
        """First pass: Update entity fields and observations.

        Updates everything except relations and sets null checksum
        to indicate sync not complete.
        """
        logger.debug(f"Updating entity without relations: {path_id}")
        db_entity = await self.get_by_path_id(path_id)

        # Update fields from markdown
        db_entity.name = markdown.content.title
        db_entity.entity_type = markdown.frontmatter.type
        db_entity.description = markdown.content.description

        # Update observations
        db_entity.observations = [
            Observation(content=obs.content) for obs in markdown.content.observations
        ]

        # Mark as incomplete
        db_entity.checksum = None

        return await self.repository.update(
            db_entity.id,
            {
                "name": db_entity.name,
                "entity_type": db_entity.entity_type,
                "description": db_entity.description,
                "observations": db_entity.observations,
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
        db_entity = await self.get_by_path_id(markdown.frontmatter.id)

        # get all entities from relations
        target_entity_path_ids = [rel.target for rel in markdown.content.relations]
        target_entities = await self.repository.find_by_path_ids(target_entity_path_ids)
        
        # zip dict by path
        entity_by_path: Dict[str, EntityModel] = dict(zip(target_entity_path_ids, target_entities))
        
        # Update relations from markdown
        db_entity.to_relations = [
            Relation(
                from_id=db_entity.id, 
                to_id=entity_by_path[rel.target].id,
                relation_type=rel.type,
                context=rel.context,
            )
            for rel in markdown.content.relations
        ]

        # Set final checksum to mark sync complete
        db_entity.checksum = checksum

        return await self.repository.update(
            db_entity.id, {"relations": db_entity.relations, "checksum": checksum}
        )
