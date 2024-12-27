"""Entity operations for knowledge service."""

from typing import Sequence, List

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.services.entity_service import EntityService
from basic_memory.services.exceptions import EntityNotFoundError
from .file_operations import FileOperations


class EntityOperations:
    """Entity operations for knowledge service."""

    def __init__(self, 
        entity_service: EntityService,
        file_operations: FileOperations
    ):
        self.entity_service = entity_service
        self.file_operations = file_operations

    async def get_by_path_id(self, path_id: str) -> EntityModel:
        """Get entity by path ID."""
        return await self.entity_service.get_by_path_id(path_id)    

    async def create_entity(self, entity: EntitySchema) -> EntityModel:
        """Create a new entity and write to filesystem."""
        logger.debug(f"Creating entity: {entity}")

        db_entity = None
        try:
            # 1. Create entity in DB
            db_entity = await self.entity_service.create_entity(entity)

            # 2. Write file and get checksum
            _, checksum = await self.file_operations.write_entity_file(db_entity)

            # 3. Update DB with checksum
            updated = await self.entity_service.update_entity(
                db_entity.path_id, {"checksum": checksum}
            )

            return updated

        except Exception as e:
            # Clean up on any failure
            if db_entity:
                await self.entity_service.delete_entity(db_entity.path_id)
                await self.file_operations.delete_entity_file(db_entity)
            logger.error(f"Failed to create entity: {e}")
            raise

    async def create_entities(self, entities: List[EntitySchema]) -> Sequence[EntityModel]:
        """Create multiple entities."""
        logger.debug(f"Creating {len(entities)} entities")
        created = []

        for entity in entities:
            created_entity = await self.create_entity(entity)
            created.append(created_entity)
            
        return created

    async def delete_entity(self, path_id: str) -> bool:
        """Delete entity and its file."""
        logger.debug(f"Deleting entity: {path_id}")

        try:
            # Get entity first for file deletion
            entity = await self.entity_service.get_by_path_id(path_id)

            # Delete file first (it's source of truth)
            await self.file_operations.delete_entity_file(entity)

            # Delete from DB (this will cascade to observations/relations)
            return await self.entity_service.delete_entity(path_id)
        
        except EntityNotFoundError:
            logger.info(f"Entity not found: {path_id}")
            return True # Already deleted
        
        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            raise

    async def delete_entities(self, path_ids: List[str]) -> bool:
        """Delete multiple entities and their files."""
        logger.debug(f"Deleting entities: {path_ids}")
        success = True

        for path_id in path_ids:
            await self.delete_entity(path_id)
            success = True

        return success