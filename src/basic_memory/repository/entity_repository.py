"""Repository for managing Entity objects."""
from typing import Optional, Sequence
from sqlalchemy import select, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import selectinload

from basic_memory.models import Entity, Observation
from basic_memory.repository import Repository


class EntityRepository(Repository[Entity]):
    """Repository for Entity model with memory-specific operations."""
    
    def __init__(self, session):
        super().__init__(session, Entity)

    async def find_by_id(self, entity_id: str) -> Optional[Entity]:
        """Find entity by ID with all relationships eagerly loaded."""
        try:
            # First load base entity
            result = await self.session.execute(
                select(Entity).filter(Entity.id == entity_id)
            )
            entity = result.scalars().one()
            
            # Force refresh of all relationships
            await self.refresh(entity, ['observations', 'outgoing_relations', 'incoming_relations'])
            
            return entity
        except NoResultFound:
            return None

    async def find_by_name(self, name: str) -> Optional[Entity]:
        """Find an entity by its unique name."""
        query = (
            select(Entity)
            .filter(Entity.name == name)
        )
        result = await self.session.execute(query)
        entity = result.scalars().one_or_none()
        if entity:
            await self.refresh(entity, ['observations', 'outgoing_relations', 'incoming_relations'])
        return entity
    
    async def search_by_type(self, entity_type: str, skip: int = 0, limit: int = 100) -> Sequence[Entity]:
        """Search for entities of a specific type."""
        query = select(Entity).filter(Entity.entity_type == entity_type).offset(skip).limit(limit)
        result = await self.execute_query(query)
        return result.scalars().all()

    async def search(self, query: str) -> Sequence[Entity]:
        """Search entities using LIKE pattern matching."""
        stmt = select(Entity).distinct().where(
            or_(
                Entity.name.ilike(f"%{query}%"),
                Entity.entity_type.ilike(f"%{query}%"),
                Entity.observations.any(
                    Observation.content.ilike(f"%{query}%")
                )
            )
        ).options(
            selectinload(Entity.observations),
            selectinload(Entity.outgoing_relations),
            selectinload(Entity.incoming_relations)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())