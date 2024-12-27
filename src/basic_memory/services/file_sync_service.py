"""Service for syncing files with the database."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Dict, Protocol, TypeVar, Generic, List, Optional

from loguru import logger

from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.utils.file_utils import compute_checksum


@dataclass
class FileState:
    """State of a file including path and checksum info."""
    path: str
    checksum: str
    normalized_path: str  # For comparison
    moved_from: Optional[str] = None


@dataclass
class SyncReport:
    """Report of sync results."""
    new: Set[str] = field(default_factory=set)
    modified: Set[str] = field(default_factory=set)
    deleted: Set[str] = field(default_factory=set)
    moved: Dict[str, FileState] = field(default_factory=dict)  # new_path -> state
    checksums: Dict[str, str] = field(default_factory=dict)  # path -> checksum

    @property
    def total_changes(self) -> int:
        return len(self.new) + len(self.modified) + len(self.deleted) + len(self.moved)


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
                rel_path = str(path.relative_to(directory))
                files[rel_path] = checksum
                logger.debug(f"Found file: {rel_path} with checksum: {checksum[:8]}")
            except Exception as e:
                logger.error(f"Failed to read {path}: {e}")

        logger.debug(f"Found {len(files)} markdown files")
        return files

    async def find_changes(
            self,
            directory: Path,
            get_records: callable,
            normalize_path: callable = lambda x: x,
            get_record_path: callable = lambda x: x.path_id
    ) -> SyncReport:
        """
        Find changes between filesystem and database.

        Args:
            directory: Directory to check
            get_records: Function to get database records
            normalize_path: Function to normalize paths for comparison
            get_record_path: Function to get path from record

        Returns:
            SyncReport detailing changes
        """
        # Get current files and checksums
        current_files = await self.scan_directory(directory)
        logger.debug("Current files from filesystem:")
        for path, checksum in sorted(current_files.items()):
            logger.debug(f"  {path} ({checksum[:8]})")

        # Track checksums for display
        report = SyncReport()
        for path, checksum in current_files.items():
            report.checksums[path] = checksum

        # Build DB state with normalized paths
        db_records = await get_records()
        db_files: Dict[str, tuple[str, str]] = {
            normalize_path(get_record_path(record)): (get_record_path(record), record.checksum)
            for record in db_records
        }
        
        logger.debug("Files from database:")
        for norm_path, (orig_path, checksum) in sorted(db_files.items()):
            logger.debug(f"  {norm_path} ({checksum[:8]}) [original: {orig_path}]")

        # Track files by checksum to detect moves
        checksum_locations: Dict[str, List[str]] = {}
        for path, checksum in current_files.items():
            norm_path = normalize_path(path)
            locations = checksum_locations.setdefault(checksum, [])
            locations.append(norm_path)

        processed_current = set()
        processed_db = set()

        # First pass - check for unchanged and modified files
        for curr_path, curr_checksum in current_files.items():
            norm_curr_path = normalize_path(curr_path)
            if norm_curr_path in db_files:
                db_orig_path, db_checksum = db_files[norm_curr_path]
                processed_current.add(norm_curr_path)
                processed_db.add(norm_curr_path)
                
                if curr_checksum != db_checksum:
                    logger.debug(f"Modified: {curr_path} (checksum changed)")
                    report.modified.add(curr_path)

        # Second pass - look for moves
        for curr_path, curr_checksum in current_files.items():
            norm_curr_path = normalize_path(curr_path)
            if norm_curr_path in processed_current:
                continue

            # Look for files with same checksum in DB
            was_move = False
            for db_norm_path, (db_orig_path, db_checksum) in db_files.items():
                if db_norm_path in processed_db:
                    continue
                if curr_checksum == db_checksum:
                    logger.debug(f"Moved: {db_orig_path} -> {curr_path}")
                    report.moved[curr_path] = FileState(
                        path=curr_path,
                        checksum=curr_checksum,
                        normalized_path=norm_curr_path,
                        moved_from=db_orig_path
                    )
                    processed_current.add(norm_curr_path)
                    processed_db.add(db_norm_path)
                    was_move = True
                    break
            
            if not was_move:
                logger.debug(f"New: {curr_path}")
                report.new.add(curr_path)
                processed_current.add(norm_curr_path)

        # Remaining DB files must be deleted
        for db_norm_path, (db_orig_path, _) in db_files.items():
            if db_norm_path not in processed_db:
                logger.debug(f"Deleted: {db_orig_path}")
                report.deleted.add(db_orig_path)

        # Log summary
        logger.debug(f"Changes found: {report.total_changes}")
        logger.debug(f"  New: {len(report.new)}")
        logger.debug(f"  Modified: {len(report.modified)}")
        logger.debug(f"  Deleted: {len(report.deleted)}")
        logger.debug(f"  Moved: {len(report.moved)}")

        return report

    async def find_document_changes(self, directory: Path) -> SyncReport:
        """Find changes in document directory."""
        def normalize_doc_path(path: str) -> str:
            """Normalize document paths."""
            return str(Path(path))

        return await self.find_changes(
            directory=directory,
            get_records=self.document_repository.find_all,
            normalize_path=normalize_doc_path
        )

    async def find_knowledge_changes(self, directory: Path) -> SyncReport:
        """Find changes in knowledge directory."""
        def normalize_entity_path(path: str) -> str:
            """Normalize entity paths."""
            path = path.lower()
            if path.endswith('.md'):
                path = path[:-3]
            return path

        def get_entity_path(entity) -> str:
            """Get path from entity record."""
            path = entity.path_id
            if not path.endswith('.md'):
                path = f"{path}.md"
            return path

        return await self.find_changes(
            directory=directory,
            get_records=self.entity_repository.find_all,
            normalize_path=normalize_entity_path,
            get_record_path=get_entity_path
        )