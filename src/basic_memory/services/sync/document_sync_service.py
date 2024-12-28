"""Service for syncing documents between filesystem and database."""

from pathlib import Path

from loguru import logger

from basic_memory.services import DocumentService
from basic_memory.services import FileChangeScanner
from basic_memory.services.sync. utils import SyncReport


class DocumentSyncService:
    """
    Service for syncing documents between filesystem and database.
    Handles bulk synchronization operations by composing the file scanner 
    and document service.
    """

    def __init__(self, 
        scanner: FileChangeScanner, 
        document_service: DocumentService
    ):
        self.scanner = scanner
        self.document_service = document_service

    async def sync(self, directory: Path) -> SyncReport:
        """
        Sync filesystem changes to documents in DB.
        Filesystem is treated as the source of truth.
        """
        # Find all changes
        changes = await self.scanner.find_document_changes(directory)
        
        logger.debug(f"Syncing {changes.total_changes} document changes")

        # Process new files
        for path in changes.new:
            content = (directory / path).read_text()
            logger.debug(f"Creating new document: {path}")
            await self.document_service.create_document(
                path_id=path,
                content=content
            )

        # Process modified files
        for path in changes.modified:
            content = (directory / path).read_text()
            logger.debug(f"Updating modified document: {path}")
            await self.document_service.update_document_by_path_id(
                path_id=path,
                content=content
            )

        # Process moved files
        for new_path, state in changes.moved.items():
            logger.debug(f"Moving document from {state.moved_from} to {new_path}")
            content = (directory / new_path).read_text()
            
            # Delete old document and create new one
            await self.document_service.delete_document_by_path_id(state.moved_from)
            await self.document_service.create_document(
                path_id=new_path,
                content=content
            )

        # Process deleted files
        for path in changes.deleted:
            logger.debug(f"Deleting document: {path}")
            await self.document_service.delete_document_by_path_id(path)

        return changes