"""Service for syncing files with the database."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Set

from loguru import logger

from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.utils.file_utils import compute_checksum


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

    def __init__(self, document_repository: DocumentRepository):
        self.repository = document_repository

    async def scan_files(self, directory: Path) -> dict[str, str]:
        """
        Scan directory for markdown files and their checksums.
        Only processes .md files, logs and skips other files.

        Args:
            directory: Root directory to scan

        Returns:
            Dict mapping paths to checksums

        Raises:
            SyncError: If any markdown file cannot be read
        """
        logger.debug(f"Scanning directory: {directory}")
        files = {}
        errors = []

        for path in directory.rglob('*'):
            if path.is_file():
                if not path.name.endswith('.md'):
                    logger.debug(f"Skipping non-markdown file: '{path}'")
                    continue

                try:
                    content = path.read_text()
                    checksum = await compute_checksum(content)
                    # Store path relative to root directory
                    rel_path = str(path.relative_to(directory))
                    files[rel_path] = checksum
                except Exception as e:
                    errors.append(f"Failed to read {path}: {e}")
                logger.debug(f"Scanned file: {path} checksum: {checksum}")
        if errors:
            raise SyncError("Failed to read files:\n" + "\n".join(errors))

        logger.debug(f"Found {len(files)} markdown files in {directory}")
        return files

    async def find_changes(self, file_system_files: dict[str, str], directory: Path) -> SyncReport:
        """
        Find changes between filesystem and database.
        Only considers files that belong to the specified directory.

        Args:
            file_system_files: Dict mapping paths to checksums
            directory: Root directory being scanned (knowledge/ or documents/)

        Returns:
            SyncReport detailing changes
        """
        logger.debug(f"Finding changes in {directory}")
        
        # Get all documents from DB
        db_documents = await self.repository.find_all()
        
        # Filter DB files to only those in this directory
        db_files = {
            doc.path: doc.checksum 
            for doc in db_documents
            if Path(doc.path).is_relative_to(directory.name)  # e.g., 'knowledge/' or 'documents/'
        }

        logger.debug(f"Found {len(db_files)} files in DB for {directory}")

        # Find changes
        new = set(file_system_files.keys()) - set(db_files.keys())
        deleted = set(db_files.keys()) - set(file_system_files.keys())
        modified = {
            path for path in file_system_files
            if path in db_files and file_system_files[path] != db_files[path]
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
            checksum = await self.compute_checksum(content)
            await self.repository.create({
                "path": path,
                "checksum": checksum
            })
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
            checksum = await self.compute_checksum(content)
            doc = await self.repository.find_by_path(path)
            if doc:
                await self.repository.update(doc.id, {"checksum": checksum})
            else:
                await self.repository.create({
                    "path": path,
                    "checksum": checksum
                })
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
        changes = await self.find_changes(current_files, directory)
        logger.info(f"Found changes in {directory}: {changes}")

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
            doc = await self.repository.find_by_path(path)
            if doc:
                await self.repository.delete(doc.id)

        logger.info("Sync completed successfully")
        return changes