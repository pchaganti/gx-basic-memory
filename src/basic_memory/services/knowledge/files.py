"""File operations for knowledge service."""

from pathlib import Path

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.services.exceptions import EntityNotFoundError, FileOperationError
from basic_memory.services.file_service import FileService
from basic_memory.services.entity_service import EntityService
from basic_memory.markdown.knowledge_writer import KnowledgeWriter


class FileOperations:
    """File operations mixin for KnowledgeService."""

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

    def get_entity_path(self, entity: EntityModel) -> Path:
        """Generate filesystem path for entity."""
        # Store in entities/[type]/[name].md
        return self.base_path / "knowledge" / entity.entity_type / f"{entity.name}.md"

    async def write_entity_file(self, entity: EntityModel) -> str:
        """Write entity to filesystem and return checksum."""
        try:
            # Ensure we have a fresh entity with all relations loaded
            entity = await self.entity_service.get_entity(entity.id)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {entity.id}")

            # Format content
            path = self.get_entity_path(entity)
            entity_content = await self.knowledge_writer.format_content(entity)
            file_content = await self.file_service.add_frontmatter(
                id=entity.id,
                content=entity_content,
                created=entity.created_at,
                updated=entity.updated_at,
            )

            # Write and get checksum
            return await self.file_service.write_file(path, file_content)

        except Exception as e:
            logger.error(f"Failed to write entity file: {e}")
            raise FileOperationError(f"Failed to write entity file: {e}")