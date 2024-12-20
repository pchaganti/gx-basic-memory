"""Service for managing relations in the database."""

from typing import List, Dict, Any

from loguru import logger

from basic_memory.models import Relation as RelationModel
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.schemas import Entity as EntitySchema, Relation
from .service import BaseService


class RelationService(BaseService[RelationRepository]):
    """
    Service for managing relations in the database.
    File operations are handled by MemoryService.
    """

    def __init__(self, relation_repository: RelationRepository):
        super().__init__(relation_repository)

    async def create_relation(self, relation: Relation) -> RelationModel:
        """Create a new relation in the database."""
        logger.debug(f"Creating relation: {relation}")
        return await self.repository.create(relation.model_dump())

    async def delete_relation(
        self, from_entity: EntitySchema, to_entity: EntitySchema, relation_type: str
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

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> bool:
        """Delete relations matching specified criteria."""
        logger.debug(f"Deleting {len(relations)} relations")
        deleted = False
        for relation in relations:
            filters = {"from_id": relation["from_id"], "to_id": relation["to_id"]}
            if "relation_type" in relation:
                filters["relation_type"] = relation["relation_type"]

            result = await self.repository.delete_by_fields(**filters)
            if result:
                deleted = True

        return deleted

    async def create_relations(self, relations_data: List[Relation]) -> List[RelationModel]:
        """Create multiple relations between entities."""
        logger.debug(f"Creating {len(relations_data)} relations")
        return await self.repository.create_all(
            [Relation.model_dump(relation) for relation in relations_data]
        )
