"""Repository for managing Entity objects."""
from typing import Optional, Sequence
from sqlalchemy import select, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import selectinload

from basic_memory.models import Entity, Observation
from basic_memory.repository import Repository
from loguru import logger


class EntityRepository(Repository[Entity]):
    """Repository for Entity model with memory-specific operations."""
    
    def __init__(self, session):
        super().__init__(session, Entity)
        logger.debug("Initialized EntityRepository")

    async def find_by_id(self, entity_id: str) -> Optional[Entity]:
        """Find entity by ID with all relationships eagerly loaded."""
        logger.debug(f"Finding entity by ID: {entity_id}")
        try:
            # First load base entity
            result = await self.session.execute(
                select(Entity).filter(Entity.id == entity_id)
            )
            entity = result.scalars().one()
            logger.debug(f"Found base entity: {entity.id}")
            
            # Force refresh of all relationships
            await self.refresh(entity, ['observations', 'outgoing_relations', 'incoming_relations'])
            logger.debug(f"Refreshed entity relationships: {entity.id}")
            
            return entity
        except NoResultFound:
            logger.debug(f"No entity found with ID: {entity_id}")
            return None
        except Exception as e:
            logger.exception(f"Error finding entity by ID: {entity_id}")
            raise

    async def find_by_name(self, name: str) -> Optional[Entity]:
        """Find an entity by its unique name."""
        logger.debug(f"Finding entity by name: {name}")
        try:
            query = (
                select(Entity)
                .filter(Entity.name == name)
            )
            result = await self.session.execute(query)
            entity = result.scalars().one_or_none()
            if entity:
                logger.debug(f"Found entity: {entity.id}")
                await self.refresh(entity, ['observations', 'outgoing_relations', 'incoming_relations'])
                logger.debug(f"Refreshed entity relationships: {entity.id}")
            else:
                logger.debug(f"No entity found with name: {name}")
            return entity
        except Exception as e:
            logger.exception(f"Error finding entity by name: {name}")
            raise
    
    async def search_by_type(self, entity_type: str, skip: int = 0, limit: int = 100) -> Sequence[Entity]:
        """Search for entities of a specific type."""
        logger.debug(f"Searching entities by type: {entity_type} (skip={skip}, limit={limit})")
        try:
            query = select(Entity).filter(Entity.entity_type == entity_type).offset(skip).limit(limit)
            result = await self.execute_query(query)
            entities = result.scalars().all()
            logger.debug(f"Found {len(entities)} entities of type {entity_type}")
            return entities
        except Exception as e:
            logger.exception(f"Error searching entities by type: {entity_type}")
            raise

    async def search(self, query: str) -> Sequence[Entity]:
        """Search entities using LIKE pattern matching."""
        logger.debug(f"Searching entities with query: {query}")
        try:
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
            entities = list(result.scalars())
            logger.debug(f"Found {len(entities)} matching entities")
            return entities
        except Exception as e:
            logger.exception(f"Error searching entities: {query}")
            raise