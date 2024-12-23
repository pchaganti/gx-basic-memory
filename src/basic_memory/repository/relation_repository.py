"""Repository for managing Relation objects."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from basic_memory.models import Relation
from basic_memory.repository.repository import Repository


class RelationRepository(Repository[Relation]):
    """Repository for Relation model with memory-specific operations."""

    def __init__(self, session_maker: async_sessionmaker):
        super().__init__(session_maker, Relation)

    async def create(self, data: dict) -> Relation:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Create with eagerly loaded entities."""
        created = await super().create(data)
        # Refresh with relations loaded
        query = (
            select(Relation)
            .where(Relation.id == created.id)
            .options(
                selectinload(Relation.from_entity),
                selectinload(Relation.to_entity),
            )
        )
        result = await self.execute_query(query)
        return result.scalars().one()
        
    async def find_by_entity(self, from_entity_id: int) -> Sequence[Relation]:
        """Find all relations from a specific entity."""
        query = (
            select(Relation)
            .filter(Relation.from_id == from_entity_id)
            .options(
                selectinload(Relation.from_entity),
                selectinload(Relation.to_entity)
            )
        )
        result = await self.execute_query(query)
        return result.scalars().all()

    async def find_by_entities(self, from_id: int, to_id: int) -> Sequence[Relation]:
        """Find all relations between two entities."""
        query = (
            select(Relation)
            .where(
                (Relation.from_id == from_id) &
                (Relation.to_id == to_id)
            )
            .options(
                selectinload(Relation.from_entity),
                selectinload(Relation.to_entity)
            )
        )
        result = await self.execute_query(query)
        return result.scalars().all()

    async def find_by_type(self, relation_type: str) -> Sequence[Relation]:
        """Find all relations of a specific type."""
        query = (
            select(Relation)
            .filter(Relation.relation_type == relation_type)
            .options(
                selectinload(Relation.from_entity),
                selectinload(Relation.to_entity)
            )
        )
        result = await self.execute_query(query)
        return result.scalars().all()