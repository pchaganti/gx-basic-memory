"""Service for file operations with checksum tracking."""

import hashlib
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import yaml
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
            return await file_utils.compute_checksum(content)

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
        self, content: str, id: int, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add YAML frontmatter to content.

        Args:
            content: Content to add frontmatter to
            id: ID to include in frontmatter
            metadata: Optional additional metadata

        Returns:
            Content with frontmatter added

        Raises:
            FileOperationError: If frontmatter creation fails
        """
        try:
            # Generate frontmatter with timestamps
            now = datetime.now(UTC).isoformat()
            frontmatter = {"id": id, "created": now, "modified": now}
            if metadata:
                frontmatter.update(metadata)

            return await file_utils.add_frontmatter(content, frontmatter)

        except Exception as e:
            logger.error(f"Failed to add frontmatter: {e}")
            raise FileOperationError(f"Failed to add frontmatter: {e}")
