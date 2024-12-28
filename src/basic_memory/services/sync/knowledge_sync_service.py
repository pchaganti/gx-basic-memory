from pathlib import Path

from basic_memory.markdown import KnowledgeParser
from basic_memory.services import FileChangeScanner, KnowledgeService
from basic_memory.services.sync.utils import FileState, SyncReport


class KnowledgeSyncService:
    def __init__(
        self,
        scanner: FileChangeScanner,
        knowledge_service: KnowledgeService,
        knowledge_parser: KnowledgeParser,
    ):
        self.scanner = scanner
        self.knowledge_service = knowledge_service
        self.knowledge_parser = knowledge_parser

    async def sync_new_entity(self, directory: Path, path: str) -> None:
        """Handle syncing a new entity file."""
        entity = await self.knowledge_parser.parse_file(directory / path)
        await self.knowledge_service.create_entity(entity)

    async def sync_modified_entity(self, directory: Path, path: str) -> None:
        """Handle syncing a modified entity file."""
        entity = await self.knowledge_parser.parse_file(directory / path)
        # TODO: Update vs create, preserve relations
        await self.knowledge_service.create_entity(entity)

    async def sync_moved_entity(self, directory: Path, new_path: str, state: FileState) -> None:
        """Handle syncing a moved entity file."""
        new_entity = await self.knowledge_parser.parse_file(directory / new_path)
        old_entity = await self.knowledge_service.get_entity_by_path_id(state.moved_from)
        # TODO: Preserve relations, update paths
        await self.knowledge_service.create_entity(new_entity)

    async def sync_deleted_entity(self, path: str) -> None:
        """Handle syncing a deleted entity file."""
        await self.knowledge_service.delete_entity(path)

    async def sync(self, directory: Path) -> SyncReport:
        """Sync knowledge files between filesystem and database."""
        # Find all changes
        changes = await self.scanner.find_knowledge_changes(directory)

        # Process each type of change
        for path in changes.new:
            await self.sync_new_entity(directory, path)

        for path in changes.modified:
            await self.sync_modified_entity(directory, path)

        for new_path, state in changes.moved.items():
            await self.sync_moved_entity(directory, new_path, state)

        for path in changes.deleted:
            await self.sync_deleted_entity(path)

        return changes
