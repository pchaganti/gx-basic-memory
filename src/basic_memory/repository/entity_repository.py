"""Repository for managing entities in the knowledge graph."""

from typing import List, Optional, Dict, Any, Sequence

from loguru import logger
from sqlalchemy import select, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from basic_memory import db
from basic_memory.models.knowledge import Entity, Observation, Relation
from basic_memory.repository.repository import Repository


class EntityRepository(Repository[Entity]):
    """Repository for Entity model."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        """Initialize with session maker."""
        super().__init__(session_maker, Entity)

    async def create(self, data: dict) -> Entity:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Create a new entity in the database from the provided data."""
        created = await super().create(data)

        # we have to find to get relations
        found = await self.find_by_id(created.id)
        assert found is not None, f"Created entity {created} should not be None"
        return found

    async def create_all(self, data_list: List[dict]) -> Sequence[Entity]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Create a new entity in the database from the provided data."""
        created = await super().create_all(data_list)
        # we have to find to get relations
        return await self.find_by_ids([e.id for e in created])

    async def find_by_id(self, entity_id: int) -> Optional[Entity]:
        """Find entity by ID with all relationships eagerly loaded."""
        logger.debug(f"Finding entity by ID: {entity_id}")
        async with db.scoped_session(self.session_maker) as session:
            try:
                result = await session.execute(
                    select(Entity)
                    .filter(Entity.id == entity_id)
                    .options(
                        selectinload(Entity.observations),
                        selectinload(Entity.from_relations).selectinload(Relation.to_entity),
                        selectinload(Entity.to_relations).selectinload(Relation.from_entity),
                    )
                )
                entity = result.scalars().one()
                logger.debug(f"Found entity: {entity.id}")
                return entity
            except NoResultFound:
                logger.debug(f"No entity found with ID: {entity_id}")
                return None

    async def find_by_ids(self, ids: List[int]) -> Sequence[Entity]:
        """Search for entities by IDs with all relationships loaded."""
        logger.debug(f"Find entities by ids: {ids}")
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(
                select(Entity)
                .where(self.primary_key.in_(ids))
                .options(
                    selectinload(Entity.observations),
                    selectinload(Entity.from_relations).selectinload(Relation.to_entity),
                    selectinload(Entity.to_relations).selectinload(Relation.from_entity),
                )
            )
            entities = result.scalars().all()
            logger.debug(f"Found {len(entities)}")
            return entities

    async def get_entity_by_type_and_name(self, entity_type: str, name: str) -> Optional[Entity]:
        """Get entity by type and name."""
        query = (
            self.select()
            .options(
                selectinload(Entity.observations),
                selectinload(Entity.from_relations).selectinload(Relation.to_entity),
                selectinload(Entity.to_relations).selectinload(Relation.from_entity),
            )
            .where(Entity.entity_type == entity_type, Entity.name == name)
        )
        return await self.find_one(query)

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        doc_id: Optional[int] = None,
    ) -> Sequence[Entity]:
        """List all entities, optionally filtered by type."""
        query = (
            self.select()
            .options(
                selectinload(Entity.observations),
                selectinload(Entity.from_relations).selectinload(Relation.to_entity),
                selectinload(Entity.to_relations).selectinload(Relation.from_entity),
            )
        )

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
            .options(
                selectinload(Entity.observations),
                selectinload(Entity.from_relations).selectinload(Relation.to_entity),
                selectinload(Entity.to_relations).selectinload(Relation.from_entity),
            )
        )
        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def update_entity(self, entity_id: int, updates: Dict[str, Any]) -> Optional[Entity]:
        """Update an entity with the given fields."""
        return await self.update(entity_id, updates)

    async def delete_entities_by_doc_id(self, doc_id: int) -> bool:
        """Delete all entities associated with a document."""
        return await self.delete_by_fields(doc_id=doc_id)