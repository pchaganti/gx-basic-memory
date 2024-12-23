"""Relation operations for knowledge service."""

from typing import Sequence, List

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Relation as RelationSchema
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.relation_service import RelationService
from .entities import EntityOperations


class RelationOperations(EntityOperations):
    """Relation operations mixin for KnowledgeService."""

    def __init__(self, *args, relation_service: RelationService, **kwargs):
        super().__init__(*args, **kwargs)
        self.relation_service = relation_service

    async def create_relations(self, relations: List[RelationSchema]) -> Sequence[EntityModel]:
        """Create relations and return updated entities."""
        logger.debug(f"Creating {len(relations)} relations")
        updated_entities = []
        update_entity_ids = set()

        for relation in relations:
            try:
                # Create relation in DB
                await self.relation_service.create_relation(relation)

                # Keep track of entities we need to update
                update_entity_ids.add(relation.from_id)
                update_entity_ids.add(relation.to_id)

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
                continue

        # Get fresh copies of all updated entities
        for entity_id in update_entity_ids:
            try:
                # Get fresh entity
                entity = await self.entity_service.get_entity(entity_id)
                if not entity:
                    raise EntityNotFoundError(f"Entity not found: {entity_id}")

                # Write updated file
                checksum = await self.write_entity_file(entity)
                updated = await self.entity_service.update_entity(entity_id, {"checksum": checksum})

                updated_entities.append(updated)

            except Exception as e:
                logger.error(f"Failed to update entity {entity_id}: {e}")
                continue

        return updated_entities
