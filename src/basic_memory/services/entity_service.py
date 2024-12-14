"""Service for managing entities in the database."""
from pathlib import Path
from typing import List, Dict, Any, Sequence

from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import EntityIn
from basic_memory.models import Entity
from basic_memory.fileio import EntityNotFoundError
from loguru import logger


class EntityService:
    """
    Service for managing entities in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, entity_repo: EntityRepository):
        self.project_path = project_path
        self.entity_repo = entity_repo
        logger.debug(f"Initialized EntityService with path: {project_path}")

    async def search(self, query: str) -> Sequence[Entity]:
        """Search entities using LIKE pattern matching."""
        logger.debug(f"Searching entities with query: {query}")
        try:
            results = await self.entity_repo.search(query)
            logger.debug(f"Found {len(results)} matches")
            return results
        except Exception:
            logger.exception(f"Failed to search entities with query: {query}")
            raise

    async def create_entity(self, entity: EntityIn) -> Entity:
        """Create a new entity in the database."""
        logger.debug(f"Creating entity in DB: {entity}")
        try:
            created_entity = await self.entity_repo.create(entity.model_dump())
            logger.debug(f"Created base entity: {created_entity.id}")

            await self.entity_repo.refresh(created_entity, ['observations', 'outgoing_relations', 'incoming_relations'])
            logger.debug(f"Refreshed entity relationships: {created_entity.id}")

            return created_entity
        except Exception:
            logger.exception(f"Failed to create entity: {entity}")
            raise

    async def update_entity(self, entity_id: str, update_data: Dict[str, Any]) -> Entity:
        """Update an entity's fields."""
        logger.debug(f"Updating entity {entity_id} with data: {update_data}")
        try:
            updated = await self.entity_repo.update(entity_id, update_data)
            if not updated:
                raise EntityNotFoundError(f"Entity not found: {entity_id}")
            
            logger.debug(f"Updated entity: {updated.id}")
            return updated
        except EntityNotFoundError:
            raise
        except Exception:
            logger.exception(f"Failed to update entity: {entity_id}")
            raise

    async def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID."""
        logger.debug(f"Getting entity by ID: {entity_id}")
        try:
            db_entity = await self.entity_repo.find_by_id(entity_id)
            if not db_entity:
                logger.error(f"Entity not found: {entity_id}")
                raise EntityNotFoundError(f"Entity not found: {entity_id}")

            logger.debug(f"Found entity: {db_entity.id}")
            return db_entity
        except EntityNotFoundError:
            raise
        except Exception:
            logger.exception(f"Failed to get entity: {entity_id}")
            raise

    async def get_by_type_and_name(self, entity_type: str, name: str) -> Entity:
        """Get entity by type and name combination."""
        logger.debug(f"Getting entity by type/name: {entity_type}/{name}")
        try:
            db_entity = await self.entity_repo.find_by_type_and_name(entity_type, name)
            if not db_entity:
                logger.error(f"Entity not found: {entity_type}/{name}")
                raise EntityNotFoundError(f"Entity not found: {entity_type}/{name}")

            logger.debug(f"Found entity: {db_entity.id}")
            return db_entity
        except EntityNotFoundError:
            raise
        except Exception:
            logger.exception(f"Failed to get entity by type/name: {entity_type}/{name}")
            raise

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from database."""
        logger.debug(f"Deleting entity: {entity_id}")
        try:
            result = await self.entity_repo.delete(entity_id)
            logger.debug(f"Entity deleted: {entity_id}")
            return result
        except Exception:
            logger.exception(f"Failed to delete entity: {entity_id}")
            raise