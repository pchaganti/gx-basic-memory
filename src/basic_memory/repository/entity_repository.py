"""Repository for managing entities in the knowledge graph."""

from typing import List, Optional, Sequence

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from basic_memory.models.knowledge import Entity, Observation, Relation
from basic_memory.repository.repository import Repository


class EntityRepository(Repository[Entity]):
    """Repository for Entity model."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        """Initialize with session maker."""
        super().__init__(session_maker, Entity)

    async def get_entity_by_type_and_name(self, entity_type: str, name: str) -> Optional[Entity]:
        """Get entity by type and name."""
        query = (
            self.select()
            .options(*self.get_load_options())
            .where(Entity.entity_type == entity_type, Entity.name == name)
        )
        return await self.find_one(query)

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        doc_id: Optional[int] = None,
    ) -> Sequence[Entity]:
        """List all entities, optionally filtered by type."""
        query = self.select().options(*self.get_load_options())

        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if doc_id:
            query = query.where(Entity.doc_id == doc_id)

        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def get_entity_types(self) -> List[str]:
        """Get list of distinct entity types."""
        query = select(Entity.entity_type).distinct()

        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def search(self, query_str: str) -> List[Entity]:
        """
        Search for entities.

        Searches across:
        - Entity names
        - Entity types
        - Entity descriptions
        - Associated Observations content
        """
        search_term = f"%{query_str}%"
        query = (
            self.select()
            .where(
                or_(
                    Entity.name.ilike(search_term),
                    Entity.entity_type.ilike(search_term),
                    Entity.description.ilike(search_term),
                    Entity.observations.any(Observation.content.ilike(search_term)),
                )
            )
            .options(*self.get_load_options())
        )
        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def delete_entities_by_doc_id(self, doc_id: int) -> bool:
        """Delete all entities associated with a document."""
        return await self.delete_by_fields(doc_id=doc_id)

    def get_load_options(self) -> List[LoaderOption]:
        return [
            selectinload(Entity.observations),
            selectinload(Entity.from_relations).selectinload(Relation.to_entity),
            selectinload(Entity.to_relations).selectinload(Relation.from_entity),
        ]
