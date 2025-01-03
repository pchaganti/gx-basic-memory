"""Service for detecting changes between filesystem and database."""

from pathlib import Path
from typing import Dict, Protocol, TypeVar, Optional, Sequence

from loguru import logger

from basic_memory.models import Document, Entity
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.services.sync.utils import FileState, SyncReport, ScanResult
from basic_memory.utils.file_utils import compute_checksum


class DbRecord(Protocol):
    """Protocol for database records with path and checksum."""
    @property
    def file_path(self) -> Optional[str]: ...
    @property
    def path_id(self) -> str: ...
    @property
    def checksum(self) -> Optional[str]: ...


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
                    result.files[rel_path] = FileState(
                        path=rel_path,
                        checksum=checksum
                    )
                    logger.debug(f"Found file: {rel_path} ({checksum[:8]})")
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
            self,
            directory: Path,
            db_records: Dict[str, FileState]
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
        scan_result = await self.scan_directory(directory)
        current_files = scan_result.files
        
        logger.debug("Current files from filesystem:")
        for path, state in sorted(current_files.items()):
            logger.debug(f"  {path} ({state.checksum[:8]})")

        
        logger.debug("Files from database:")
        for path, state in sorted(db_records.items()):
            logger.debug(f"  {path} ({state.checksum[:8]})")

        # Build report
        report = SyncReport()
        
        # Add current checksums for display
        for path, state in current_files.items():
            report.checksums[path] = state.checksum
        
        # Find new and modified files
        for path, curr_state in current_files.items():
            if path not in db_records:
                report.new.add(path)
            elif curr_state.checksum != db_records[path].checksum:
                report.modified.add(path)

        # Find deleted files
        report.deleted = set(db_records.keys()) - set(current_files.keys())

        # Log summary
        logger.debug(f"Changes found: {report.total_changes}")
        logger.debug(f"  New: {len(report.new)}")
        logger.debug(f"  Modified: {len(report.modified)}")
        logger.debug(f"  Deleted: {len(report.deleted)}")
        
        if scan_result.errors:
            logger.warning("Files skipped due to errors:")
            for path, error in scan_result.errors.items():
                logger.warning(f"  {path}: {error}")

        return report

    async def get_db_state(self, db_records: Sequence[Document | Entity ]) -> Dict[str, FileState]:
        """Get current files and checksums from database.

        Args:
            get_records: Function to query database records

        Returns:
            Dict mapping paths to FileState
            :param db_records: the data from the db 
        """
        db_files = {}

        for record in db_records:
            # TODO - why file_path?
            # Use file_path if available, otherwise use path_id
            path = record.file_path if record.file_path is not None else record.path_id

            if record.checksum:
                db_files[record.path_id] = FileState(
                    path=record.path_id,
                    checksum=record.checksum
                )

        return db_files

    async def find_document_changes(self, directory: Path) -> SyncReport:
        """Find changes in document directory."""
        db_records = await self.get_db_state(await self.document_repository.find_all())
        return await self.find_changes(
            directory=directory,
            db_records=db_records
        )

    async def find_knowledge_changes(self, directory: Path) -> SyncReport:
        """Find changes in knowledge directory."""
        db_records = await self.get_db_state(await self.entity_repository.find_all())
        return await self.find_changes(
            directory=directory,
            db_records=db_records
        )