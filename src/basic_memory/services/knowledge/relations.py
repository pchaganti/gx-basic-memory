"""Relation operations for knowledge service."""

from typing import Sequence, List

from loguru import logger

from basic_memory.schemas import Relation as RelationSchema
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.relation_service import RelationService
from .entities import EntityOperations


class RelationOperations(EntityOperations):
    """Relation operations mixin for KnowledgeService."""

    def __init__(self, *args, relation_service: RelationService, **kwargs):
        super().__init__(*args, **kwargs)
        self.relation_service = relation_service

    async def create_relations(self, relations: List[RelationSchema]) -> Sequence[RelationSchema]:
        """Create relations and update affected entity files."""
        logger.debug(f"Creating {len(relations)} relations")
        created = []

        for relation in relations:
            try:
                # Create relation in DB
                db_relation = await self.relation_service.create_relation(relation)

                # Update files with their new relations
                for entity_id in [relation.from_id, relation.to_id]:
                    # Get fresh entity
                    entity = await self.entity_service.get_entity(entity_id)
                    if not entity:
                        raise EntityNotFoundError(f"Entity not found: {entity_id}")

                    # Write updated file
                    checksum = await self.write_entity_file(entity)
                    await self.entity_service.update_entity(entity_id, {"checksum": checksum})

                created.append(db_relation)

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
                continue

        return created