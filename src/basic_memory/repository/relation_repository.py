"""Repository for managing Relation objects."""

from typing import Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import async_sessionmaker

from basic_memory.models import Relation
from basic_memory.repository.repository import Repository


class RelationRepository(Repository[Relation]):
    """Repository for Relation model with memory-specific operations."""

    def __init__(self, session_maker: async_sessionmaker):
        super().__init__(session_maker, Relation)

    async def find_by_entity(self, from_entity_id: int) -> Sequence[Relation]:
        """Find all relations from a specific entity."""
        query = select(Relation).filter(Relation.from_id == from_entity_id)
        result = await self.execute_query(query)
        return result.scalars().all()

    async def find_by_entities(self, from_id: int, to_id: int) -> Sequence[Relation]:
        """Find all relations between two entities."""
        query = select(Relation).filter(and_(Relation.from_id == from_id, Relation.to_id == to_id))
        result = await self.execute_query(query)
        return result.scalars().all()

    async def find_by_type(self, relation_type: str) -> Sequence[Relation]:
        """Find all relations of a specific type."""
        query = select(Relation).filter(Relation.relation_type == relation_type)
        result = await self.execute_query(query)
        return result.scalars().all()
