"""Service for syncing files between filesystem and database."""

from pathlib import Path
from typing import Dict

from loguru import logger

from basic_memory.markdown import EntityParser, EntityMarkdown
from basic_memory.repository import EntityRepository
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.entity_sync_service import EntitySyncService
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
        entity_sync_service: EntitySyncService,
        entity_parser: EntityParser,
        entity_repository: EntityRepository,
        search_service: SearchService,
    ):
        self.scanner = scanner
        self.entity_sync_service = entity_sync_service
        self.entity_parser = entity_parser
        self.entity_repository = entity_repository
        self.search_service = search_service

    async def sync(self, directory: Path) -> SyncReport:
        """Sync knowledge files with database."""
        changes = await self.scanner.find_knowledge_changes(directory)
        logger.info(f"Found {changes.total_changes} knowledge changes")

        # Handle deletions first
        # remove rows from db for files no longer present
        for file_path in changes.deleted:
            logger.debug(f"Deleting entity from db: {file_path}")
            await self.entity_sync_service.delete_entity_by_file_path(file_path)

        # Parse files that need updating
        parsed_entities: Dict[str, EntityMarkdown] = {}

        for file_path in [*changes.new, *changes.modified]:
            entity_markdown = await self.entity_parser.parse_file(directory / file_path)
            parsed_entities[file_path] = entity_markdown

        # First pass: Create/update entities
        # entities will have a null checksum to indicate they are not complete
        for file_path, entity_markdown in parsed_entities.items():
            # if the file is new, create an entity
            if file_path in changes.new:
                logger.debug(f"Creating new entity_markdown: {file_path}")
                await self.entity_sync_service.create_entity_from_markdown(
                    file_path, entity_markdown
                )
            # otherwise we need to update the entity and observations
            else:
                logger.debug(f"Updating entity_markdown: {file_path}")
                await self.entity_sync_service.update_entity_and_observations(
                    file_path, entity_markdown
                )

        # Second pass
        for file_path, entity_markdown in parsed_entities.items():
            logger.debug(f"Updating relations for: {file_path}")
            
            # Process relations
            checksum = changes.checksums[file_path]
            entity = await self.entity_sync_service.update_entity_relations(file_path, entity_markdown)
            
            # add to search index
            await self.search_service.index_entity(entity)

            # Set final checksum to mark sync complete
            await self.entity_repository.update(entity.id, {"checksum": checksum})

        return changes
