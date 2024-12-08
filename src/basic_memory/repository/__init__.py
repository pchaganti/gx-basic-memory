"""Base repository implementation."""
from typing import Type, Optional, Any, Sequence, TypeVar
from sqlalchemy import select, func, Select, Executable, inspect, Result, Column
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from basic_memory.models import Base

T = TypeVar('T', bound=Base)

class Repository[T: Base]:
    """Base repository implementation with generic CRUD operations."""

    def __init__(self, session: AsyncSession, Model: Type[T]):
        self.session = session
        self.Model = Model
        self.primary_key: Column[Any] = inspect(self.Model).mapper.primary_key[0]
        self.valid_columns = [column.key for column in inspect(self.Model).columns]

    async def refresh(self, instance: T, relationships: list[str] | None = None) -> None:
        """Refresh instance and optionally specified relationships."""
        await self.session.refresh(instance, relationships or [])

    async def find_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        """Fetch records from the database with pagination."""
        result = await self.session.execute(
            select(self.Model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """Fetch an entity by its unique identifier."""
        try:
            result = await self.session.execute(
                select(self.Model).filter(self.primary_key == entity_id)
            )
            return result.scalars().one()
        except NoResultFound:
            return None

    async def create(self, entity_data: dict, model: Type[Base] | None = None) -> T:
        """Create a new entity in the database from the provided data."""
        model = model or self.Model
        model_data = {k: v for k, v in entity_data.items() if k in self.valid_columns}
        entity = model(**model_data)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity_id: str, entity_data: dict) -> Optional[T]:
        """Update an entity with the given data."""
        try:
            result = await self.session.execute(
                select(self.Model).filter(self.primary_key == entity_id)
            )
            entity = result.scalars().one()
            for key, value in entity_data.items():
                if key in self.valid_columns:
                    setattr(entity, key, value)
            await self.session.flush()
            return entity
        except NoResultFound:
            return None

    async def delete(self, entity_id: str) -> bool:
        """Delete an entity from the database."""
        try:
            result = await self.session.execute(
                select(self.Model).filter(self.primary_key == entity_id)
            )
            entity = result.scalars().one()
            await self.session.delete(entity)
            await self.session.flush()
            return True
        except NoResultFound:
            return False

    async def count(self, query: Executable | None = None) -> int:
        """Count entities in the database table."""
        if query is None:
            query = select(func.count()).select_from(self.Model)
        result = await self.session.execute(query)
        scalar = result.scalar()
        return scalar if scalar is not None else 0

    async def execute_query(self, query: Executable) -> Result[Any]:
        """Execute a query asynchronously."""
        return await self.session.execute(query)

    async def find_one(self, query: Select[tuple[T]]) -> Optional[T]:
        """Execute a query and retrieve a single record."""
        result = await self.execute_query(query)
        return result.scalars().one_or_none()
