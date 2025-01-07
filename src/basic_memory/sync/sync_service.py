"""Service for syncing files between filesystem and database."""

from pathlib import Path

from loguru import logger

from basic_memory.config import ProjectConfig
from basic_memory.markdown import KnowledgeParser
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.knowledge_sync_service import KnowledgeSyncService
from basic_memory.sync.utils import SyncReport


class SyncService:
    """Syncs documents and knowledge files with database.

    Implements two-pass sync strategy for knowledge files to handle relations:
    1. First pass creates/updates entities without relations
    2. Second pass processes relations after all entities exist
    """

    def __init__(
        self,
        scanner: FileChangeScanner,
        knowledge_sync_service: KnowledgeSyncService,
        knowledge_parser: KnowledgeParser,
        search_service: SearchService,
    ):
        self.scanner = scanner
        self.knowledge_sync_service = knowledge_sync_service
        self.knowledge_parser = knowledge_parser
        self.search_service = search_service


    async def sync_knowledge(self, directory: Path) -> SyncReport:
        """Sync knowledge files with database."""
        changes = await self.scanner.find_knowledge_changes(directory)
        logger.info(f"Found {changes.total_changes} knowledge changes")

        # Handle deletions first
        # remove rows from db for files no longer present
        for file_path in changes.deleted:
            logger.debug(f"Deleting entity from db: {file_path}")
            await self.knowledge_sync_service.delete_entity_by_file_path(file_path)

        # Parse files that need updating
        parsed_entities = {}
        for file_path in [*changes.new, *changes.modified]:
            entity_markdown = await self.knowledge_parser.parse_file(directory / file_path)
            parsed_entities[file_path] = entity_markdown

        # First pass: Create/update entities
        for file_path, entity_markdown in parsed_entities.items():
            if file_path in changes.new:
                logger.debug(f"Creating new entity_markdown: {file_path}")
                await self.knowledge_sync_service.create_entity_and_observations(
                    file_path, entity_markdown
                )
            else:
                path_id = entity_markdown.frontmatter.id
                logger.debug(f"Updating entity_markdown: {path_id}")
                await self.knowledge_sync_service.update_entity_and_observations(
                    path_id, entity_markdown
                )

        # Second pass: Process relations
        for file_path, entity_markdown in parsed_entities.items():
            logger.debug(f"Updating relations for: {file_path}")
            entity = await self.knowledge_sync_service.update_entity_relations(
                entity_markdown, checksum=changes.checksums[file_path]
            )
            # add to search index
            await self.search_service.index_entity(entity)

        return changes

    async def sync(self, config: ProjectConfig) -> SyncReport:
        """Sync all files with database."""
        knowledge_changes = await self.sync_knowledge(config.knowledge_dir)
        return knowledge_changes
