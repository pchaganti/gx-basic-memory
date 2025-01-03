"""Service for managing relations in the database."""

from typing import List, Dict, Any, Sequence

from loguru import logger

from basic_memory.models import Entity, Relation
from basic_memory.repository.relation_repository import RelationRepository
from .service import BaseService


class RelationService(BaseService[RelationRepository]):
    """
    Service for managing relations in the database.
    File operations are handled by MemoryService.
    """

    def __init__(self, relation_repository: RelationRepository):
        super().__init__(relation_repository)

    async def create_relation(self, relation: Relation) -> Relation:
        """Create a new relation in the database."""
        logger.debug(f"Creating relation: {relation}")
        return await self.repository.add(relation)

    async def find_relation(self, from_path_id: str, to_path_id: str, relation_type: str) -> Relation:
        return await self.repository.find_relation(from_path_id, to_path_id, relation_type)
        
    async def delete_relation(
        self, from_entity: Entity, to_entity: Entity, relation_type: str
    ) -> bool:
        """Delete a specific relation between entities."""
        logger.debug(f"Deleting relation between {from_entity.id} and {to_entity.id}")

        assert from_entity.id is not None, "from_entity.id must not be None"
        result = await self.repository.delete_by_fields(
            from_id=from_entity.id,
            to_id=to_entity.id,
            relation_type=relation_type,
        )
        return result

    async def delete_relations(self, relations: List[Relation]) -> int:
        """Delete relations matching specified criteria."""
        logger.debug(f"Deleting {len(relations)} relations")
        
        ids = [relation.id for relation in relations]
        return await self.repository.delete_by_ids(ids)

    async def create_relations(self, relations: List[Relation]) -> Sequence[Relation]:
        """Create multiple relations between entities."""
        logger.debug(f"Creating {len(relations)} relations")
        return await self.repository.add_all(relations)

    async def delete_outgoing_relations_from_entity(self, entity_id: int) -> None:
        logger.debug(f"Deleting outgoing relations from {entity_id} ")
        return await self.repository.delete_outgoing_relations_from_entity(entity_id)