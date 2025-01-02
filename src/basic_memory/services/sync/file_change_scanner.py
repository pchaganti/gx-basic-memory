"""Service for detecting changes between filesystem and database."""

from pathlib import Path
from typing import Dict, Protocol, TypeVar, Optional

from loguru import logger

from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.services.sync.utils import FileState, SyncReport
from basic_memory.utils.file_utils import compute_checksum


class DbRecord(Protocol):
    """Protocol for database records with path and checksum."""
    @property
    def file_path(self) -> Optional[str]: ...
    @property
    def path_id(self) -> str: ...
    @property
    def checksum(self) -> str: ...


T = TypeVar('T', bound=DbRecord)


class FileChangeScanner:
    """
    Service for detecting changes between filesystem and database.
    The filesystem is treated as the source of truth.
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

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping relative paths to checksums
        """
        logger.debug(f"Scanning directory: {directory}")
        files = {}

        if not directory.exists():
            logger.debug(f"Directory does not exist: {directory}")
            return files

        for path in directory.rglob("*"):
            if not path.is_file() or not path.name.endswith(".md"):
                if path.is_file():
                    logger.debug(f"Skipping non-markdown file: {path}")
                continue

            try:
                content = path.read_text()
                checksum = await compute_checksum(content)
                rel_path = str(path.relative_to(directory))
                files[rel_path] = checksum
                logger.debug(f"Found file: {rel_path} with checksum: {checksum[:8] if checksum else 'None'}")
            except Exception as e:
                logger.error(f"Failed to read {path}: {e}")

        logger.debug(f"Found {len(files)} markdown files")
        return files

    async def find_changes(
            self,
            directory: Path,
            get_records: callable
    ) -> SyncReport:
        """
        Find changes between filesystem and database.

        Args:
            directory: Directory to check
            get_records: Function to get database records

        Returns:
            SyncReport detailing changes
        """
        # Get current files and checksums
        current_files = await self.scan_directory(directory)
        logger.debug("Current files from filesystem:")
        for path, checksum in sorted(current_files.items()):
            logger.debug(f"  {path} ({checksum[:8] if checksum else 'No checksum'})")

        # Track checksums for display
        report = SyncReport()
        for path, checksum in current_files.items():
            if checksum:  # Only store valid checksums
                report.checksums[path] = checksum

        # Build DB state - use path_id if file_path is NULL
        db_records = await get_records()
        db_files = {}
        for record in db_records:
            if record and hasattr(record, 'path_id'):  # Guard against None records
                path = record.file_path if record.file_path is not None else record.path_id
                db_files[path] = (path, record.checksum)

        logger.debug("Files from database:")
        for path, (_, checksum) in sorted(db_files.items()):
            logger.debug(f"  {path} ({checksum[:8] if checksum else 'No checksum'})")

        # Track files by checksum for move detection
        db_paths_by_checksum = {}
        for path, (_, checksum) in db_files.items():
            if checksum:  # Only track valid checksums
                paths = db_paths_by_checksum.setdefault(checksum, [])
                paths.append(path)

        processed_current = set()
        processed_db = set()

        # First pass - check for unchanged and modified files
        for curr_path, curr_checksum in current_files.items():
            if curr_path in db_files:
                _, db_checksum = db_files[curr_path]
                processed_current.add(curr_path)
                processed_db.add(curr_path)
                
                if curr_checksum != db_checksum:
                    logger.debug(f"Modified: {curr_path} (checksum changed)")
                    report.modified.add(curr_path)

        # Second pass - look for moves
        for curr_path, curr_checksum in current_files.items():
            if curr_path in processed_current:
                continue

            # Look for any files with same checksum in DB
            was_move = False
            if curr_checksum and curr_checksum in db_paths_by_checksum:  # Only check valid checksums
                for db_path in db_paths_by_checksum[curr_checksum]:
                    if db_path not in processed_db:
                        logger.debug(f"Moved: {db_path} -> {curr_path}")
                        report.moved[curr_path] = FileState(
                            path=curr_path,
                            checksum=curr_checksum,
                            moved_from=db_path
                        )
                        processed_current.add(curr_path)
                        processed_db.add(db_path)
                        was_move = True
                        break

            if not was_move:
                logger.debug(f"New: {curr_path}")
                report.new.add(curr_path)
                processed_current.add(curr_path)

        # Remaining DB files must be deleted
        for path, (db_path, _) in db_files.items():
            if path not in processed_db:
                logger.debug(f"Deleted: {db_path}")
                report.deleted.add(db_path)

        # Log summary
        logger.debug(f"Changes found: {report.total_changes}")
        logger.debug(f"  New: {len(report.new)}")
        logger.debug(f"  Modified: {len(report.modified)}")
        logger.debug(f"  Deleted: {len(report.deleted)}")
        logger.debug(f"  Moved: {len(report.moved)}")

        return report

    async def find_document_changes(self, directory: Path) -> SyncReport:
        """Find changes in document directory."""
        return await self.find_changes(
            directory=directory,
            get_records=self.document_repository.find_all
        )

    async def find_knowledge_changes(self, directory: Path) -> SyncReport:
        """Find changes in knowledge directory."""
        return await self.find_changes(
            directory=directory,
            get_records=self.entity_repository.find_all
        )