"""File operations for knowledge service."""

from pathlib import Path
from typing import Tuple

from loguru import logger

from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Entity as EntityModel
from basic_memory.services.entity_service import EntityService
from basic_memory.services.exceptions import FileOperationError
from basic_memory.services.file_service import FileService


class FileOperations:
    """File operations for knowledge entities."""

    def __init__(
        self,
        entity_service: EntityService,
        file_service: FileService,
        knowledge_writer: KnowledgeWriter,
        base_path: Path,
    ):
        self.entity_service = entity_service
        self.file_service = file_service
        self.knowledge_writer = knowledge_writer
        self.base_path = base_path

    async def file_exists(self, path: Path) -> bool:
        return await self.file_service.exists(path)

    async def read_file(self, path: Path) -> Tuple[str, str]:
        return await self.file_service.read_file(path)

    def get_entity_path(self, entity: EntityModel) -> Path:
        """Generate filesystem path for entity."""
        return self.base_path / entity.entity_type / f"{entity.name}.md"

    async def write_entity_file(self, entity: EntityModel) -> Tuple[Path, str]:
        """Write entity to filesystem and return path and checksum."""
        try:
            # Ensure we have a fresh entity with all relations loaded
            entity = await self.entity_service.get_by_path_id(entity.path_id)

            # Format content
            path = self.get_entity_path(entity)
            entity_content = await self.knowledge_writer.format_content(entity)
            file_content = await self.file_service.add_frontmatter(
                id=entity.path_id,
                content=entity_content,
                created=entity.created_at,
                updated=entity.updated_at,
            )

            # Write and get checksum
            return path, await self.file_service.write_file(path, file_content)

        except Exception as e:
            logger.error(f"Failed to write entity file: {e}")
            raise FileOperationError(f"Failed to write entity file: {e}")

    async def delete_entity_file(self, entity: EntityModel) -> None:
        """Delete entity file from filesystem."""
        try:
            path = self.get_entity_path(entity)
            await self.file_service.delete_file(path)
        except Exception as e:
            logger.error(f"Failed to delete entity file: {e}")
            raise FileOperationError(f"Failed to delete entity file: {e}")