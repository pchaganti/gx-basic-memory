"""Entity operations for knowledge service."""

from datetime import datetime, UTC
from typing import Sequence, List, Dict, Any, Optional, Tuple

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

    async def read_entity_content(self, entity: EntityModel) -> str:
        """Get entity's content if it's a note.

        Args:
            path_id: Entity's path ID

        Returns:
            content without frontmatter

        Raises:
            FileOperationError: If entity file doesn't exist
        """
        logger.debug(f"Reading entity with path_id: {entity.path_id}")

            
        # For notes, read the actual file content
        file_path = self.file_operations.get_entity_path(entity)
        content, _ = await self.file_operations.read_file(file_path)
        # Strip frontmatter from content
        _, _, content = content.split("---", 2)
        return content.strip()

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

    async def update_entity(
            self,
            path_id: str,
            content: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            **update_fields: Any
    ) -> EntityModel:
        """Update an entity's content and metadata.

        Args:
            path_id: Entity's path ID
            content: Optional new content
            metadata: Optional metadata updates
            **update_fields: Additional entity fields to update

        Returns:
            Updated entity

        Raises:
            EntityNotFoundError: If entity doesn't exist
        """
        logger.debug(f"Updating entity with path_id: {path_id}")

        # Get existing entity
        entity = await self.entity_service.get_by_path_id(path_id)
        if not entity:
            raise EntityNotFoundError(f"Entity not found: {path_id}")

        try:
            # Build update data
            update_data = {}

            # Add any direct field updates
            if update_fields:
                update_data.update(update_fields)

            # Handle metadata update
            if metadata is not None:
                # Update existing metadata
                new_metadata = dict(entity.entity_metadata or {})
                new_metadata.update(metadata)
                update_data["entity_metadata"] = new_metadata

            # Update entity in database if we have changes
            if update_data:
                entity = await self.entity_service.update_entity(
                    entity.path_id, update_data
                )

            # Always write file if we have any updates
            if update_data or content is not None:
                _, checksum = await self.file_operations.write_entity_file(
                    entity=entity,
                    content=content
                )
                # Update checksum in DB
                entity = await self.entity_service.update_entity(
                    entity.path_id, {"checksum": checksum}
                )

            return entity

        except Exception as e:
            logger.error(f"Failed to update entity: {e}")
            raise

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