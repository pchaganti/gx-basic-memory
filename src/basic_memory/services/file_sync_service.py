"""Service for syncing files with the database."""

from dataclasses import dataclass
from pathlib import Path
from typing import Set, Dict, Protocol, TypeVar, Generic

from loguru import logger

from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
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


class DbRecord(Protocol):
    """Protocol for database records with path and checksum."""
    @property
    def path(self) -> str: ...
    @property
    def checksum(self) -> str: ...


T = TypeVar('T', bound=DbRecord)


class FileSyncService:
    """
    Service for keeping files and database in sync.
    The filesystem is the source of truth.
    """

    def __init__(
        self, 
        document_repository: DocumentRepository,
        entity_repository: EntityRepository
    ):
        self.document_repository = document_repository
        self.entity_repository = entity_repository

    async def scan_directory(self, directory: Path) -> Dict[str, str]:
        """
        Scan directory for markdown files and their checksums.
        Only processes .md files, logs and skips others.
        Keeps .md extension for filesystem source of truth.

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping relative paths to checksums
        """
        logger.debug(f"Scanning directory: {directory}")
        files = {}

        for path in directory.rglob("*"):
            if not path.is_file() or not path.name.endswith(".md"):
                if path.is_file():
                    logger.debug(f"Skipping non-markdown file: {path}")
                continue

            try:
                content = path.read_text()
                checksum = await compute_checksum(content)
                # Keep .md for filesystem source of truth
                rel_path = str(path.relative_to(directory))
                files[rel_path] = checksum
            except Exception as e:
                logger.error(f"Failed to read {path}: {e}")

        logger.debug(f"Found {len(files)} markdown files")
        return files

    async def find_changes(
            self,
            directory: Path,
            get_records: callable,
            get_path: callable = lambda x: x.path
    ) -> SyncReport:
        """
        Find changes between filesystem and database.

        Args:
            directory: Directory to check
            get_records: Function to get database records
            get_path: Function to get path from record (defaults to .path)

        Returns:
            SyncReport detailing changes
        """
        # Get current files and checksums
        current_files = await self.scan_directory(directory)
        logger.debug("Current files from filesystem:")
        for path in sorted(current_files.keys()):
            logger.debug(f"  {path}")

        # Get database records
        db_records = await get_records()
        db_files = {
            get_path(record): record.checksum
            for record in db_records
        }
        logger.debug("Files from database:")
        for path in sorted(db_files.keys()):
            logger.debug(f"  {path}")

        # Compare current vs database state
        new = set(current_files.keys()) - set(db_files.keys())
        logger.debug("New files (in filesystem but not db):")
        for path in sorted(new):
            logger.debug(f"  {path}")

        deleted = set(db_files.keys()) - set(current_files.keys())
        logger.debug("Deleted files (in db but not filesystem):")
        for path in sorted(deleted):
            logger.debug(f"  {path}")

        modified = {
            path for path in current_files
            if path in db_files and current_files[path] != db_files[path]
        }
        logger.debug("Modified files (checksum mismatch):")
        for path in sorted(modified):
            logger.debug(f"  {path}")

        return SyncReport(new=new, modified=modified, deleted=deleted)

    async def find_document_changes(self, directory: Path) -> SyncReport:
        """Find changes in document directory."""
        return await self.find_changes(
            directory=directory,
            get_records=self.document_repository.find_all
        )

    async def find_knowledge_changes(self, directory: Path) -> SyncReport:
        """Find changes in knowledge directory."""
        # For knowledge files, we need to strip .md to match entity.path_id
        def get_path_without_md(entity):
            """Get entity path_id, ensuring no .md extension."""
            path = entity.path_id
            if path.endswith('.md'):
                path = path[:-3]
            return path

        return await self.find_changes(
            directory=directory,
            get_records=self.entity_repository.find_all,
            get_path=get_path_without_md
        )