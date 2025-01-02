"""File change detection for sync service."""

import hashlib
from pathlib import Path
from typing import Dict, Set

from loguru import logger

from basic_memory.repository.document import DocumentRepository
from basic_memory.repository.entity import EntityRepository
from basic_memory.services.sync.utils import SyncReport


class FileChangeScanner:
    """Detects changes between filesystem and database state."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        entity_repository: EntityRepository,
    ):
        self.document_repository = document_repository
        self.entity_repository = entity_repository

    async def calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(path, "rb") as f:
            # Read file in chunks to handle large files
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
                
        return sha256_hash.hexdigest()

    async def find_document_changes(self, directory: Path) -> SyncReport:
        """Find changes in document files."""
        return await self._find_changes(directory, self.document_repository)

    async def find_knowledge_changes(self, directory: Path) -> SyncReport:
        """Find changes in knowledge files."""
        return await self._find_changes(directory, self.entity_repository)

    async def _scan_filesystem(self, directory: Path) -> Dict[str, str]:
        """Scan directory and get current files with checksums."""
        current_files = {}
        
        if not directory.exists():
            return current_files
            
        for path in directory.rglob("*.md"):
            if path.is_file():
                rel_path = str(path.relative_to(directory))
                checksum = await self.calculate_checksum(path)
                current_files[rel_path] = checksum
                
        return current_files

    async def _get_db_state(self, repository) -> Dict[str, str]:
        """Get current files and checksums from database."""
        db_files = {}
        
        async with repository.session() as session:
            results = await repository.list_with_checksums(session)
            for path, checksum in results:
                if checksum:  # Only include files that completed sync
                    db_files[path] = checksum
                    
        return db_files

    async def _find_changes(self, directory: Path, repository) -> SyncReport:
        """Find changes between filesystem and database state."""
        # Get current states
        current_files = await self._scan_filesystem(directory)
        db_files = await self._get_db_state(repository)

        # Build report
        report = SyncReport()
        report.checksums = current_files

        # Find deleted files (in DB but not filesystem)
        report.deleted = set(db_files.keys()) - set(current_files.keys())

        # Find new and modified files
        for path, current_checksum in current_files.items():
            if path not in db_files:
                report.new.add(path)
            elif current_checksum != db_files[path]:
                report.modified.add(path)

        # Log summary
        logger.debug(
            f"Found {len(report.new)} new, {len(report.modified)} modified, "
            f"and {len(report.deleted)} deleted files"
        )

        return report
