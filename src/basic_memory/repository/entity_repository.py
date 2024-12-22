"""Repository for managing entities in the knowledge graph."""
from typing import List, Optional, Dict, Any, Sequence
from datetime import datetime

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql import text

from basic_memory import db
from basic_memory.models.knowledge import Entity
from basic_memory.repository.repository import Repository


class EntityRepository(Repository[Entity]):
    """Repository for Entity model."""

    async def create_entity(
        self, 
        name: str, 
        entity_type: str, 
        description: Optional[str] = None,
        path: Optional[str] = None,
        checksum: Optional[str] = None,
        doc_id: Optional[int] = None,
    ) -> Entity:
        """Create a new entity."""
        data = {
            "name": name,
            "entity_type": entity_type,
            "description": description,
            "path": path,
            "checksum": checksum,
            "doc_id": doc_id,
        }
        return await self.create(data)

    async def get_entity_by_type_and_name(
        self, entity_type: str, name: str
    ) -> Optional[Entity]:
        """Get entity by type and name."""
        query = self.select().where(
            Entity.entity_type == entity_type,
            Entity.name == name
        )
        return await self.find_one(query)

    async def list_entities(
        self, 
        entity_type: Optional[str] = None,
        doc_id: Optional[int] = None,
    ) -> Sequence[Entity]:
        """List all entities, optionally filtered by type."""
        query = self.select()
        
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if doc_id:
            query = query.where(Entity.doc_id == doc_id)
            
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_entity_types(self) -> List[str]:
        """Get list of distinct entity types."""
        query = select(Entity.entity_type).distinct()
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(query)
            return [r[0] for r in result.all()]

    async def search_entities(self, query_str: str) -> List[Entity]:
        """
        Search for entities.
        
        Searches across:
        - Entity names
        - Entity types 
        - Entity descriptions
        """
        search_term = f"%{query_str}%"
        query = self.select().where(
            (Entity.name.ilike(search_term)) |
            (Entity.entity_type.ilike(search_term)) |
            (Entity.description.ilike(search_term))
        )
        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def update_entity(
        self,
        entity_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Entity]:
        """Update an entity with the given fields."""
        return await self.update(str(entity_id), updates)

    async def delete_entities_by_doc_id(self, doc_id: int) -> bool:
        """Delete all entities associated with a document."""
        return await self.delete_by_fields(doc_id=doc_id)
