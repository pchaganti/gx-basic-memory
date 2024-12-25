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

    async def get_by_path_id(self, path_id: str) -> Optional[Entity]:
        """Get entity by type and name."""
        query = self.select().where(Entity.path_id == path_id).options(*self.get_load_options())
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
            # Load from_relations and both entities for each relation
            selectinload(Entity.from_relations).selectinload(Relation.from_entity),
            selectinload(Entity.from_relations).selectinload(Relation.to_entity),
            # Load to_relations and both entities for each relation
            selectinload(Entity.to_relations).selectinload(Relation.from_entity),
            selectinload(Entity.to_relations).selectinload(Relation.to_entity),
        ]

    async def find_by_path_ids(self, path_ids: List[str]) -> Sequence[Entity]:
        """Find multiple entities by their entity_type and name pairs."""

        # Handle empty input explicitly
        if not path_ids:
            return []

        # Use existing select pattern
        query = self.select().options(*self.get_load_options()).where(Entity.path_id.in_(path_ids))

        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def delete_by_path_ids(self, path_ids: List[str]) -> int:
        """Delete multiple entities by entity_type and name pairs."""

        # Handle empty input explicitly
        if not path_ids:
            return 0

        # Find matching entities
        entities = await self.find_by_path_ids(path_ids)
        if not entities:
            return 0

        # Use existing delete_by_ids
        return await self.delete_by_ids([entity.id for entity in entities])
