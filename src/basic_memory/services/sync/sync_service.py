"""Service for syncing files between filesystem and database."""

from pathlib import Path
from loguru import logger

from basic_memory.services import FileChangeScanner, EntityService, DocumentService
from basic_memory.markdown import KnowledgeParser
from basic_memory.services.sync.knowledge_sync_service import KnowledgeSyncService


class SyncService:
    """Syncs documents and knowledge files with database.
    
    Implements two-pass sync strategy for knowledge files to handle relations:
    1. First pass creates/updates entities without relations
    2. Second pass processes relations after all entities exist
    """

    def __init__(
        self,
        scanner: FileChangeScanner,
        document_service: DocumentService,
        knowledge_sync_service: KnowledgeSyncService,
        knowledge_parser: KnowledgeParser,
    ):
        self.scanner = scanner
        self.document_service = document_service
        self.knowledge_sync_service = knowledge_sync_service
        self.knowledge_parser = knowledge_parser

    async def sync_documents(self, directory: Path) -> None:
        """Sync document files with database."""
        changes = await self.scanner.find_document_changes(directory)
        logger.info(f"Found {changes.total_changes} document changes")

        # Handle deletions first
        for path in changes.deleted:
            logger.debug(f"Deleting document: {path}")
            await self.document_service.delete_document_by_path_id(path)

        # Process new and modified files
        for path in [*changes.new, *changes.modified]:
            content = (directory / path).read_text()
            if path in changes.new:
                logger.debug(f"Creating new document: {path}")
                await self.document_service.create_document(path_id=path, content=content)
            else:
                logger.debug(f"Updating document: {path}")
                await self.document_service.update_document_by_path_id(path_id=path, content=content)

    async def sync_knowledge(self, directory: Path) -> None:
        """Sync knowledge files with database."""
        changes = await self.scanner.find_knowledge_changes(directory)
        logger.info(f"Found {changes.total_changes} knowledge changes")

        # Handle deletions first
        for path_id in changes.deleted:
            logger.debug(f"Deleting entity: {path_id}")
            await self.knowledge_sync_service.delete_entity_by_file_path(path_id)

        # Parse files that need updating
        parsed_entities = {}
        for path_id in [*changes.new, *changes.modified]:
            entity = await self.knowledge_parser.parse_file(directory / path_id)
            parsed_entities[path_id] = entity

        # First pass: Create/update entities
        for path_id, entity in parsed_entities.items():
            if path_id in changes.new:
                logger.debug(f"Creating new entity: {path_id}")
                await self.knowledge_sync_service.create_entity_and_observations(entity)
            else:
                logger.debug(f"Updating entity: {path_id}")
                await self.knowledge_sync_service.update_entity_and_observations(entity)

        # Second pass: Process relations
        for path_id, entity in parsed_entities.items():
            logger.debug(f"Updating relations for: {path_id}")
            await self.knowledge_sync_service.update_entity_relations(entity, checksum=changes.checksums[path_id])

    async def sync(self, root_dir: Path) -> None:
        """Sync all files with database."""
        # Sync documents first (simpler, no relations)
        docs_dir = root_dir / "documents"
        if docs_dir.exists():
            await self.sync_documents(docs_dir)
        
        # Then sync knowledge files
        knowledge_dir = root_dir / "knowledge"
        if knowledge_dir.exists():
            await self.sync_knowledge(knowledge_dir)