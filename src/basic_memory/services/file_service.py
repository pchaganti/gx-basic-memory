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

    async def add_frontmatter(
        self,
        *,
        frontmatter: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        content: str,
    ) -> str:
        """
        Add YAML frontmatter to content.

        Args:
            frontmatter: frontmatter info
            content: Content to add frontmatter to
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
