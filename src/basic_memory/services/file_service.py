"""Service for file operations with checksum tracking."""

from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from loguru import logger

from basic_memory.services.exceptions import FileOperationError
from basic_memory.utils import file_utils


class FileService:
    """
    Service for handling file operations.

    Features:
    - Consistent file writing with checksums
    - Frontmatter management
    - Atomic operations
    - Error handling
    """

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
            logger.debug(f"wrote file: {path}, checksum: {checksum}")
            return checksum

        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            raise FileOperationError(f"Failed to write file: {e}")

    async def read_file(self, path: Path) -> Tuple[str, str]:
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

    async def delete_file(self, path: Path) -> None:
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

    async def has_frontmatter(self, content: str) -> bool:
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

    async def parse_frontmatter(self, content: str) -> Dict[str, Any]:
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

    async def remove_frontmatter(self, content: str) -> str:
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
