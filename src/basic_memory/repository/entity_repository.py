"""Repository for managing Entity objects."""

from typing import Optional, Sequence, List

from loguru import logger
from sqlalchemy import select, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from basic_memory import db
from basic_memory.models import Entity, Observation
from basic_memory.repository.repository import Repository


class EntityRepository(Repository[Entity]):
    """Repository for Entity model with memory-specific operations."""

    def __init__(self, session_maker: async_sessionmaker):
        super().__init__(session_maker, Entity)
        logger.debug("Initialized EntityRepository")

    async def create(self, data: dict) -> Entity:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Create a new entity in the database from the provided data."""
        entity_id = Entity.generate_id(data["entity_type"], data["name"])
        await super().create({**data, "id": entity_id})

        # we have to find to get relations
        created = await self.find_by_id(entity_id)
        assert created is not None, f"Created entity {entity_id} should not be None"
        return created

    async def create_all(self, data_list: List[dict]) -> Sequence[Entity]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Create a new entity in the database from the provided data."""
        for data in data_list:
            entity_id = Entity.generate_id(data["entity_type"], data["name"])
            data["id"] = entity_id
        created = await super().create_all(data_list)
        # we have to find to get relations
        return await self.find_by_ids([e.id for e in created])

    async def find_by_id(self, entity_id: str) -> Optional[Entity]:
        """Find entity by ID with all relationships eagerly loaded."""
        logger.debug(f"Finding entity by ID: {entity_id}")
        async with db.scoped_session(self.session_maker) as session:
            try:
                result = await session.execute(
                    select(Entity)
                    .filter(Entity.id == entity_id)
                    .options(
                        selectinload(Entity.observations),
                        selectinload(Entity.outgoing_relations),
                        selectinload(Entity.incoming_relations),
                    )
                )
                entity = result.scalars().one()
                logger.debug(f"Found entity: {entity.id}")
                return entity
            except NoResultFound:
                logger.debug(f"No entity found with ID: {entity_id}")
                return None

    async def find_by_ids(self, ids: List[str]) -> Sequence[Entity]:
        """Search for entities of a specific type."""
        logger.debug(f"Find entities by ids: {ids}")
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(
                select(Entity)
                .where(self.primary_key.in_(ids))
                .options(
                    selectinload(Entity.observations),
                    selectinload(Entity.outgoing_relations),
                    selectinload(Entity.incoming_relations),
                )
            )
            entities = result.scalars().all()
            logger.debug(f"Found {len(entities)}")
            return entities

    async def find_by_name(self, name: str) -> Optional[Entity]:
        """Find an entity by its unique name."""
        logger.debug(f"Finding entity by name: {name}")
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(
                select(Entity)
                .filter(Entity.name == name)
                .options(
                    selectinload(Entity.observations),
                    selectinload(Entity.outgoing_relations),
                    selectinload(Entity.incoming_relations),
                )
            )
            entity = result.scalars().one_or_none()
            if entity:
                logger.debug(f"Found entity: {entity.id}")
            else:
                logger.debug(f"No entity found with name: {name}")
            return entity

    async def find_by_type_and_name(self, entity_type: str, name: str) -> Optional[Entity]:
        """Find an entity by its type and name combination."""
        logger.debug(f"Finding entity by type and name: {entity_type}/{name}")
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(
                select(Entity)
                .filter(Entity.entity_type == entity_type)
                .filter(Entity.name == name)
                .options(
                    selectinload(Entity.observations),
                    selectinload(Entity.outgoing_relations),
                    selectinload(Entity.incoming_relations),
                )
            )
            entity = result.scalars().one_or_none()
            if entity:
                logger.debug(f"Found entity: {entity.id}")
            else:
                logger.debug(f"No entity found with type/name: {entity_type}/{name}")
            return entity

    async def search_by_type(
        self, entity_type: str, skip: int = 0, limit: int = 100
    ) -> Sequence[Entity]:
        """Search for entities of a specific type."""
        logger.debug(f"Searching entities by type: {entity_type} (skip={skip}, limit={limit})")
        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(
                select(Entity)
                .filter(Entity.entity_type == entity_type)
                .options(
                    selectinload(Entity.observations),
                    selectinload(Entity.outgoing_relations),
                    selectinload(Entity.incoming_relations),
                )
                .offset(skip)
                .limit(limit)
            )
            entities = result.scalars().all()
            logger.debug(f"Found {len(entities)} entities of type {entity_type}")
            return entities

    async def search(self, query: str) -> Sequence[Entity]:
        """Search entities using LIKE pattern matching."""
        logger.debug(f"Searching entities with query: {query}")
        async with db.scoped_session(self.session_maker) as session:
            stmt = (
                select(Entity)
                .distinct()
                .where(
                    or_(
                        Entity.name.ilike(f"%{query}%"),
                        Entity.entity_type.ilike(f"%{query}%"),
                        Entity.observations.any(Observation.content.ilike(f"%{query}%")),
                    )
                )
                .options(
                    selectinload(Entity.observations),
                    selectinload(Entity.outgoing_relations),
                    selectinload(Entity.incoming_relations),
                )
            )
            result = await session.execute(stmt)
            entities = list(result.scalars())
            logger.debug(f"Found {len(entities)} matching entities")
            return entities
