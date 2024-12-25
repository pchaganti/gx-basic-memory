"""Entity operations for knowledge service."""

from typing import Sequence, List

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity as EntitySchema
from .files import FileOperations


class EntityOperations(FileOperations):
    """Entity operations mixin for KnowledgeService."""

    async def create_entity(self, entity: EntitySchema) -> EntityModel:
        """Create a new entity and write to filesystem."""
        logger.debug(f"Creating entity: {entity}")

        db_entity = None
        file_path = None
        try:
            # 1. Create entity in DB
            db_entity = await self.entity_service.create_entity(entity)

            # 2. Write file and get checksum
            file_path, checksum = await self.write_entity_file(db_entity)

            # 3. Update DB with checksum
            updated = await self.entity_service.update_entity(
                db_entity.path_id, {"checksum": checksum}
            )

            return updated

        except Exception as e:
            # Clean up on any failure
            if db_entity:
                await self.entity_service.delete_entity(db_entity.path_id)
            if file_path:
                await self.file_service.delete_file(file_path)
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
            if not entity:
                return True  # Already deleted

            # Delete file first (it's source of truth)
            path = self.get_entity_path(entity)
            await self.file_service.delete_file(path)

            # Delete from DB (this will cascade to observations/relations)
            return await self.entity_service.delete_entity(path_id)

        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            raise

    async def delete_entities(self, path_ids: List[str]) -> bool:
        """Delete multiple entities and their files."""
        logger.debug(f"Deleting entities: {path_ids}")
        success = True

        # Let errors bubble up
        for path_id in path_ids:
            await self.delete_entity(path_id)
            success = True

        return success
