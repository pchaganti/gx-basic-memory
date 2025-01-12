"""Service for detecting changes between filesystem and database."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Sequence

from loguru import logger

from basic_memory.models import Entity
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.sync.utils import SyncReport
from basic_memory.utils.file_utils import compute_checksum


@dataclass
class FileState:
    """State of a file including file path, permalink and checksum info."""

    file_path: str
    permalink: str
    checksum: str


@dataclass
class ScanResult:
    """Result of scanning a directory."""

    # file_path -> checksum
    files: Dict[str, str] = field(default_factory=dict)
    # file_path -> error message
    errors: Dict[str, str] = field(default_factory=dict)


class FileChangeScanner:
    """
    Service for detecting changes between filesystem and database.
    The filesystem is treated as the source of truth.
    """

    def __init__(self, entity_repository: EntityRepository):
        self.entity_repository = entity_repository

    async def scan_directory(self, directory: Path) -> ScanResult:
        """
        Scan directory for markdown files and their checksums.
        Only processes .md files, logs and skips others.

        Args:
            directory: Directory to scan

        Returns:
            ScanResult containing found files and any errors
        """
        logger.debug(f"Scanning directory: {directory}")
        result = ScanResult()

        if not directory.exists():
            logger.debug(f"Directory does not exist: {directory}")
            return result

        for path in directory.rglob("*"):
            if not path.is_file() or not path.name.endswith(".md"):
                if path.is_file():
                    logger.debug(f"Skipping non-markdown file: {path}")
                continue

            try:
                # Get relative path first - used in error reporting if needed
                rel_path = str(path.relative_to(directory))
                content = path.read_text()
                checksum = await compute_checksum(content)

                if checksum:  # Only store valid checksums
                    result.files[rel_path] = checksum
                else:
                    result.errors[rel_path] = "Failed to compute checksum"

            except Exception as e:
                rel_path = str(path.relative_to(directory))
                result.errors[rel_path] = str(e)
                logger.error(f"Failed to read {rel_path}: {e}")

        logger.debug(f"Found {len(result.files)} markdown files")
        if result.errors:
            logger.warning(f"Encountered {len(result.errors)} errors while scanning")

        return result

    async def find_changes(
        self, directory: Path, db_file_state: Dict[str, FileState]
    ) -> SyncReport:
        """
        Find changes between filesystem and database.

        Args:
            directory: Directory to check
            db_file_state: dict mapping file_path to DbState(permalink, checksum)

        Returns:
            SyncReport detailing changes
        """
        # Get current files and checksums
        scan_result = await self.scan_directory(directory)
        current_files = scan_result.files

        # Build report
        report = SyncReport()

        # Find new and modified files
        for file_path, checksum in current_files.items():
            logger.debug(f"{file_path} ({checksum[:8]})")

            if file_path not in db_file_state:
                report.new.add(file_path)
            elif checksum != db_file_state[file_path].checksum:
                report.modified.add(file_path)

            report.checksums[file_path] = checksum

        # Find deleted files - need to be deleted from db
        # either not in current_files, or
        # db row has no checksum
        for db_file_path, db_state in db_file_state.items():
            if db_file_path not in current_files:
                report.deleted.add(db_file_path)

        # Log summary
        logger.debug(f"Changes found: {report.total_changes}")
        logger.debug(f"  New: {len(report.new)}")
        logger.debug(f"  Modified: {len(report.modified)}")
        logger.debug(f"  Deleted: {len(report.deleted)}")

        if scan_result.errors:
            logger.warning("Files skipped due to errors:")
            for file_path, error in scan_result.errors.items():
                logger.warning(f"  {file_path}: {error}")

        return report

    async def get_db_file_state(self, db_records: Sequence[Entity]) -> Dict[str, FileState]:
        """Get file_path and checksums from database.
        Args:
            db_records: database records
        Returns:
            Dict mapping file paths to FileState
            :param db_records: the data from the db
        """
        return {
            r.file_path: FileState(
                file_path=r.file_path, permalink=r.permalink, checksum=r.checksum
            )
            for r in db_records
        }

    async def find_knowledge_changes(self, directory: Path) -> SyncReport:
        """Find changes in knowledge directory."""
        db_file_state = await self.get_db_file_state(await self.entity_repository.find_all())
        return await self.find_changes(directory=directory, db_file_state=db_file_state)
