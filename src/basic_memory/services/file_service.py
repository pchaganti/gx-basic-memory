"""Service for file operations with checksum tracking."""

from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from basic_memory import file_utils
from basic_memory.markdown.markdown_processor import MarkdownProcessor
from basic_memory.markdown.utils import entity_model_to_markdown
from basic_memory.models import Entity as EntityModel
from basic_memory.services.exceptions import FileOperationError


class FileService:
    """
    Service for handling file operations.

    Features:
    - Consistent file writing with checksums
    - Frontmatter management
    - Atomic operations
    - Error handling
    """

    def __init__(
        self,
        base_path: Path,
        markdown_processor: MarkdownProcessor,
    ):
        self.base_path = base_path
        self.markdown_processor = markdown_processor

    def get_entity_path(self, entity: EntityModel) -> Path:
        """Generate filesystem path for entity."""
        if entity.file_path:
            return self.base_path / entity.file_path
        return self.base_path / f"{entity.permalink}.md"

    async def write_entity_file(
        self,
        entity: EntityModel,
        content: Optional[str] = None,
        expected_checksum: Optional[str] = None,
    ) -> Tuple[Path, str]:
        """Write entity to filesystem and return path and checksum.

        Uses read->modify->write pattern:
        1. Read existing file if it exists
        2. Update with new content if provided
        3. Write back atomically

        Args:
            entity: Entity model to write
            content: Optional new content (preserves existing if None)
            expected_checksum: Optional checksum to verify file hasn't changed

        Returns:
            Tuple of (file path, new checksum)

        Raises:
            FileOperationError: If write fails
        """
        try:
            path = self.get_entity_path(entity)

            # Read current state if file exists
            if path.exists():
                # read the existing file
                existing_markdown = await self.markdown_processor.read_file(path)

                # merge content with entity
                # if content is supplied use it or existing content
                markdown = entity_model_to_markdown(
                    entity, content=content or existing_markdown.content
                )
            else:
                # Create new file structure with provided content
                markdown = entity_model_to_markdown(entity, content=content)

            # Write back atomically
            checksum = await self.markdown_processor.write_file(
                path=path, markdown=markdown, expected_checksum=expected_checksum
            )

            return path, checksum

        except Exception as e:
            logger.error(f"Failed to write entity file: {e}")
            raise FileOperationError(f"Failed to write entity file: {e}")

    async def read_entity_content(self, entity: EntityModel) -> str:
        """Get entity's content without frontmatter or structured sections.

        Args:
            entity: Entity to read content for

        Returns:
            Raw content without frontmatter, observations, or relations

        Raises:
            FileOperationError: If entity file doesn't exist
        """
        logger.debug(f"Reading entity with permalink: {entity.permalink}")

        try:
            file_path = self.get_entity_path(entity)
            markdown = await self.markdown_processor.read_file(file_path)
            return markdown.content or ""

        except Exception as e:
            logger.error(f"Failed to read entity content: {e}")
            raise FileOperationError(f"Failed to read entity content: {e}")

    async def delete_entity_file(self, entity: EntityModel) -> None:
        """Delete entity file from filesystem."""
        try:
            path = self.get_entity_path(entity)
            await self.delete_file(path)
        except Exception as e:
            logger.error(f"Failed to delete entity file: {e}")
            raise FileOperationError(f"Failed to delete entity file: {e}")

    async def exists(self, path: Path) -> bool:
        """
        Check if file exists.

        Args:
            path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            return path.exists()
        except Exception as e:
            logger.error(f"Failed to check file existence {path}: {e}")
            raise FileOperationError(f"Failed to check file existence: {e}")

    async def write_file(self, path: Path, content: str) -> str:
        """
        Write content to file and return checksum.

        Args:
            path: Path where to write
            content: Content to write

        Returns:
            Checksum of written content

        Raises:
            FileOperationError: If write fails
        """
        try:
            # Ensure parent directory exists
            await file_utils.ensure_directory(path.parent)

            # Write content atomically
            await file_utils.write_file_atomic(path, content)

            # Compute and return checksum
            checksum = await file_utils.compute_checksum(content)
            logger.debug(f"wrote file: {path}, checksum: {checksum} content: \n{content}")
            return checksum

        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            raise FileOperationError(f"Failed to write file: {e}")

    @staticmethod
    async def read_file(path: Path) -> Tuple[str, str]:
        """
        Read file and compute checksum.

        Args:
            path: Path to read

        Returns:
            Tuple of (content, checksum)

        Raises:
            FileOperationError: If read fails
        """
        try:
            content = path.read_text()
            checksum = await file_utils.compute_checksum(content)
            logger.debug(f"read file: {path}, checksum: {checksum}")
            return content, checksum

        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise FileOperationError(f"Failed to read file: {e}")

    @staticmethod
    async def delete_file(path: Path) -> None:
        """
        Delete file if it exists.

        Args:
            path: Path to delete

        Raises:
            FileOperationError: If deletion fails
        """
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            raise FileOperationError(f"Failed to delete file: {e}")
