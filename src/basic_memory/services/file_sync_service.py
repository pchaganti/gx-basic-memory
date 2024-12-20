"""Service for syncing files with the database."""

from dataclasses import dataclass
from pathlib import Path
from typing import Set

from loguru import logger

from basic_memory.services.document_service import DocumentService


@dataclass
class SyncReport:
    """Report of sync results."""
    new: Set[str]
    modified: Set[str]
    deleted: Set[str]

    @property
    def total_changes(self) -> int:
        return len(self.new) + len(self.modified) + len(self.deleted)

    def __str__(self) -> str:
        return (
            f"Changes detected:\n"
            f"  New files: {len(self.new)}\n"
            f"  Modified: {len(self.modified)}\n"
            f"  Deleted: {len(self.deleted)}"
        )


class SyncError(Exception):
    """Raised when sync operations fail."""
    pass


class FileSyncService:
    """Service for keeping files and database in sync."""

    def __init__(self, document_service: DocumentService):
        self.document_service = document_service

    async def scan_files(self, directory: Path) -> dict[str, str]:
        """
        Scan directory for files and their checksums.
        Only processes files, ignores directories.

        Args:
            directory: Root directory to scan

        Returns:
            Dict mapping paths to checksums

        Raises:
            SyncError: If any file cannot be read
        """
        logger.debug(f"Scanning directory: {directory}")
        files = {}
        errors = []

        for path in directory.rglob('*'):
            if path.is_file():
                try:
                    content = path.read_text()
                    checksum = await self.document_service.compute_checksum(content)
                    rel_path = str(path.relative_to(directory))
                    files[rel_path] = checksum
                except Exception as e:
                    errors.append(f"Failed to read {path}: {e}")

        if errors:
            raise SyncError("Failed to read files:\n" + "\n".join(errors))

        logger.debug(f"Found {len(files)} files")
        return files

    async def find_changes(self, current_files: dict[str, str]) -> SyncReport:
        """
        Find changes between filesystem and database.

        Args:
            current_files: Dict mapping paths to checksums

        Returns:
            SyncReport detailing changes
        """
        logger.debug("Finding changes")
        
        # Get all documents from DB
        db_documents = await self.document_service.list_documents()
        db_files = {
            doc.path: doc.checksum 
            for doc in db_documents
        }

        # Find changes
        new = set(current_files.keys()) - set(db_files.keys())
        deleted = set(db_files.keys()) - set(current_files.keys())
        modified = {
            path for path in current_files
            if path in db_files and current_files[path] != db_files[path]
        }

        return SyncReport(new=new, modified=modified, deleted=deleted)

    async def sync_new_file(self, path: str, directory: Path) -> None:
        """
        Sync a new file.

        Args:
            path: Relative path to file
            directory: Root directory

        Raises:
            SyncError: If sync fails
        """
        full_path = directory / path
        try:
            content = full_path.read_text()
            await self.document_service.create_document(path, content)
        except Exception as e:
            raise SyncError(f"Failed to sync new file {path}: {e}")

    async def sync_modified_file(self, path: str, directory: Path) -> None:
        """
        Sync a modified file.

        Args:
            path: Relative path to file
            directory: Root directory

        Raises:
            SyncError: If sync fails
        """
        full_path = directory / path
        try:
            content = full_path.read_text()
            await self.document_service.update_document(path, content)
        except Exception as e:
            raise SyncError(f"Failed to sync modified file {path}: {e}")

    async def sync(self, directory: Path) -> SyncReport:
        """
        Sync filesystem with database.
        Filesystem is source of truth.

        Args:
            directory: Root directory to sync

        Returns:
            SyncReport detailing changes

        Raises:
            SyncError: If sync fails
        """
        logger.info(f"Starting sync of {directory}")

        # Get current state
        current_files = await self.scan_files(directory)
        
        # Find changes
        changes = await self.find_changes(current_files)
        logger.info(f"Found changes: {changes}")

        if changes.total_changes == 0:
            logger.info("No changes detected")
            return changes

        # Process new files
        for path in changes.new:
            logger.debug(f"Processing new file: {path}")
            await self.sync_new_file(path, directory)

        # Process modified files
        for path in changes.modified:
            logger.debug(f"Processing modified file: {path}")
            await self.sync_modified_file(path, directory)

        # Process deleted files
        for path in changes.deleted:
            logger.debug(f"Processing deleted file: {path}")
            await self.document_service.delete_document(path)

        logger.info("Sync completed successfully")
        return changes