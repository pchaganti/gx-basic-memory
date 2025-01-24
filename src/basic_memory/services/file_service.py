"""Service for file operations with checksum tracking."""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from loguru import logger

from basic_memory import file_utils
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.services.exceptions import FileOperationError
from basic_memory.models import Entity as EntityModel


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
        knowledge_writer: KnowledgeWriter,
    ):
        self.base_path = base_path
        self.knowledge_writer = knowledge_writer

    def get_entity_path(self, entity: EntityModel) -> Path:
        """Generate filesystem path for entity."""
        if entity.file_path:
            return self.base_path / entity.file_path
        return self.base_path / f"{entity.permalink}.md"

    async def write_entity_file(
        self,
        entity: EntityModel,
        content: Optional[str] = None,
    ) -> Tuple[Path, str]:
        """Write entity to filesystem and return path and checksum.
        
        If content is not provided, tries to preserve existing file content.
        """
        try:
            # Try to preserve existing content if not provided
            content = await self.read_entity_content(entity) if content is None else content

            # Get frontmatter and content
            frontmatter = await self.knowledge_writer.format_frontmatter(entity)
            file_content = await self.knowledge_writer.format_content(
                entity=entity, content=content
            )

            # Add frontmatter and write
            content_with_frontmatter = await self.add_frontmatter(
                frontmatter=frontmatter, content=file_content
            )
            path = self.get_entity_path(entity)
            return path, await self.write_file(path, content_with_frontmatter)

        except Exception as e:
            logger.error(f"Failed to write entity file: {e}")
            raise FileOperationError(f"Failed to write entity file: {e}")

    async def read_entity_content(self, entity: EntityModel) -> str:
        """Get entity's content if it's a note.

        Args:
            permalink: Entity's path ID

        Returns:
            content without frontmatter

        Raises:
            FileOperationError: If entity file doesn't exist
        """
        logger.debug(f"Reading entity with permalink: {entity.permalink}")

        # For notes, read the actual file content
        file_path = self.get_entity_path(entity)
        content, _ = await self.read_file(file_path)
        if "---" in content:
            # Strip frontmatter from content
            _, _, content = content.split("---", 2)
            content = content.strip()
        return content

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

    @staticmethod
    async def has_frontmatter(content: str) -> bool:
        """
        Check if content has frontmatter markers.

        Args:
            content: Content to check

        Returns:
            True if content appears to have frontmatter
        """
        try:
            return file_utils.has_frontmatter(content)
        except Exception as e:
            logger.error(f"Failed to check frontmatter: {e}")
            return False

    @staticmethod
    async def parse_frontmatter(content: str) -> Dict[str, Any]:
        """
        Parse frontmatter from content.

        Args:
            content: Content containing frontmatter

        Returns:
            Parsed frontmatter as dict

        Raises:
            FileOperationError: If parsing fails
        """
        try:
            return file_utils.parse_frontmatter(content)
        except Exception as e:
            logger.error(f"Failed to parse frontmatter: {e}")
            raise FileOperationError(f"Failed to parse frontmatter: {e}")

    @staticmethod
    async def remove_frontmatter(content: str) -> str:
        """
        Remove frontmatter from content.

        Args:
            content: Content with frontmatter

        Returns:
            Content with frontmatter removed

        Raises:
            FileOperationError: If removal fails
        """
        try:
            return file_utils.remove_frontmatter(content)
        except Exception as e:
            logger.error(f"Failed to remove frontmatter: {e}")
            raise FileOperationError(f"Failed to remove frontmatter: {e}")

    async def remove_frontmatter_lenient(self, content: str) -> str:
        """
        Remove frontmatter without validation.

        Args:
            content: Content that may contain frontmatter

        Returns:
            Content with potential frontmatter removed
        """
        try:
            return file_utils.remove_frontmatter_lenient(content)
        except Exception as e:
            logger.error(f"Failed to remove frontmatter leniently: {e}")
            raise FileOperationError(f"Failed to remove frontmatter: {e}")

    async def add_frontmatter(
        self,
        content: str,
        frontmatter: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add YAML frontmatter to content.

        Args:
            content: Content to add frontmatter to
            frontmatter: Frontmatter to add
            metadata: Optional additional metadata

        Returns:
            Content with frontmatter added

        Raises:
            FileOperationError: If frontmatter creation fails
        """
        try:
            if metadata:
                frontmatter.update(metadata)

            return await file_utils.add_frontmatter(content, frontmatter)
        except Exception as e:
            logger.error(f"Failed to add frontmatter: {e}")
            raise FileOperationError(f"Failed to add frontmatter: {e}")

    async def write_with_frontmatter(
        self,
        path: Path,
        content: str,
        frontmatter: Dict[str, Any],
    ) -> str:
        """
        Write content to file with frontmatter, properly handling existing frontmatter.

        If content already has frontmatter, it will be updated with new values.
        If not, frontmatter will be added.

        Args:
            path: Path where to write
            content: Content to write
            frontmatter: Frontmatter to add/update

        Returns:
            Checksum of written content

        Raises:
            FileOperationError: If operation fails
        """
        try:
            final_content: str
            if await self.has_frontmatter(content):
                try:
                    # Try to parse and merge existing frontmatter
                    existing_frontmatter = await self.parse_frontmatter(content)
                    content_only = await self.remove_frontmatter(content)
                    merged_frontmatter = {**existing_frontmatter, **frontmatter}
                    final_content = await self.add_frontmatter(content_only, merged_frontmatter)
                except FileOperationError:
                    # If parsing fails, just strip any frontmatter-like content and start fresh
                    content_only = await self.remove_frontmatter_lenient(content)
                    final_content = await self.add_frontmatter(content_only, frontmatter)
            else:
                # No existing frontmatter, just add new
                final_content = await self.add_frontmatter(content, frontmatter)

            # Write and return checksum
            return await self.write_file(path, final_content)

        except Exception as e:
            logger.error(f"Failed to write file with frontmatter {path}: {e}")
            raise FileOperationError(f"Failed to write file with frontmatter: {e}")
