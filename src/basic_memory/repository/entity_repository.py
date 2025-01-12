"""Repository for managing entities in the knowledge graph."""

from typing import List, Optional, Sequence

from sqlalchemy import select, or_, asc, desc
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
        """Get entity by path_id."""
        query = self.select().where(Entity.path_id == path_id).options(*self.get_load_options())
        return await self.find_one(query)

    async def list_entities(
            self,
            entity_type: Optional[str] = None,
            sort_by: Optional[str] = "updated_at",
            include_related: bool = False,
    ) -> Sequence[Entity]:
        """List all entities, optionally filtered by type and sorted."""
        query = self.select()

        # Always load base relations
        query = query.options(*self.get_load_options())

        # Apply filters
        if entity_type:
            # When include_related is True, get both:
            # 1. Entities of the requested type
            # 2. Entities that have relations with entities of the requested type
            if include_related:
                query = query.where(
                    or_(
                        Entity.entity_type == entity_type,
                        Entity.outgoing_relations.any(Relation.to_entity.has(entity_type=entity_type)),
                        Entity.incoming_relations.any(Relation.from_entity.has(entity_type=entity_type))
                    )
                )
            else:
                query = query.where(Entity.entity_type == entity_type)

        # Apply sorting
        if sort_by:
            sort_field = getattr(Entity, sort_by, Entity.updated_at)
            query = query.order_by(asc(sort_field))

        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def get_entity_types(self) -> List[str]:
        """Get list of distinct entity types."""
        query = select(Entity.entity_type).distinct()

        result = await self.execute_query(query, use_query_options=False)
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
                    Entity.title.ilike(search_term),
                    Entity.entity_type.ilike(search_term),
                    Entity.summary.ilike(search_term),
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

    async def delete_by_file_path(self, file_path: str) -> bool:
        """Delete entity with the provided file_path."""
        return await self.delete_by_fields(file_path=file_path)

    def get_load_options(self) -> List[LoaderOption]:
        return [
            selectinload(Entity.observations),
            # Load from_relations and both entities for each relation
            selectinload(Entity.outgoing_relations).selectinload(Relation.from_entity),
            selectinload(Entity.outgoing_relations).selectinload(Relation.to_entity),
            # Load to_relations and both entities for each relation
            selectinload(Entity.incoming_relations).selectinload(Relation.from_entity),
            selectinload(Entity.incoming_relations).selectinload(Relation.to_entity),
        ]

    async def find_by_path_ids(self, path_ids: List[str]) -> Sequence[Entity]:
        """Find multiple entities by their path_id."""

        # Handle empty input explicitly
        if not path_ids:
            return []

        # Use existing select pattern
        query = self.select().options(*self.get_load_options()).where(Entity.path_id.in_(path_ids))

        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def delete_by_path_ids(self, path_ids: List[str]) -> int:
        """Delete multiple entities by path_id."""

        # Handle empty input explicitly
        if not path_ids:
            return 0

        # Find matching entities
        entities = await self.find_by_path_ids(path_ids)
        if not entities:
            return 0

        # Use existing delete_by_ids
        return await self.delete_by_ids([entity.id for entity in entities])
