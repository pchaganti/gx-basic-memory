"""Service for syncing files between filesystem and database."""

from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from basic_memory.markdown import EntityParser, EntityMarkdown
from basic_memory.repository import EntityRepository, RelationRepository
from basic_memory.services import EntityService
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.utils import SyncReport, FileChange
from watchfiles import Change


class SyncService:
    """Syncs documents and knowledge files with database.

    Implements two-pass sync strategy for knowledge files to handle relations:
    1. First pass creates/updates entities without relations
    2. Second pass processes relations after all entities exist
    """

    def __init__(
        self,
        scanner: FileChangeScanner,
        entity_service: EntityService,
        entity_parser: EntityParser,
        entity_repository: EntityRepository,
        relation_repository: RelationRepository,
        search_service: SearchService,
    ):
        self.scanner = scanner
        self.entity_service = entity_service
        self.entity_parser = entity_parser
        self.entity_repository = entity_repository
        self.relation_repository = relation_repository
        self.search_service = search_service

    async def handle_entity_deletion(self, file_path: str):
        """Handle complete entity deletion including search index cleanup."""
        # First get entity to get permalink before deletion
        entity = await self.entity_repository.get_by_file_path(file_path)
        if entity:
            logger.debug(f"Deleting entity and cleaning up search index: {file_path}")

            # Delete from db (this cascades to observations/relations)
            await self.entity_service.delete_entity_by_file_path(file_path)

            # Clean up search index
            permalinks = (
                [entity.permalink]
                + [o.permalink for o in entity.observations]
                + [r.permalink for r in entity.relations]
            )
            logger.debug(f"Deleting from search index: {permalinks}")
            for permalink in permalinks:
                await self.search_service.delete_by_permalink(permalink)

        else:
            logger.debug(f"No entity found to delete: {file_path}")

    async def sync(self, directory: Optional[Path] = None, file_changes: Optional[dict[str, FileChange]] = None) -> SyncReport:
        """Sync knowledge files with database."""
        if file_changes is not None:
            changes = SyncReport()
            for path, file_change in file_changes.items():
                logger.debug(f"path {path} file_change {file_change}")
                match file_change.change_type:
                    case Change.added:
                        changes.new.add(path)
                        changes.checksums[path] = file_change.checksum
                    case Change.modified:
                        changes.modified.add(path)
                        changes.checksums[path] = file_change.checksum
                    case Change.deleted:
                        changes.deleted.add(path)
        else:
            # Traditional directory scan mode
            if directory is None:
                raise ValueError("Must provide either directory or file_changes")
            
            changes = await self.scanner.find_knowledge_changes(directory)
            logger.info(f"Found {changes.total_changes} knowledge changes")

        # Handle moves first
        for old_path, new_path in changes.moves.items():
            logger.debug(f"Moving entity: {old_path} -> {new_path}")
            entity = await self.entity_repository.get_by_file_path(old_path)
            if entity:
                # Update file_path but keep the same permalink for link stability
                updated = await self.entity_repository.update(
                    entity.id, {"file_path": new_path, "checksum": changes.checksums[new_path]}
                )
                # update search index
                await self.search_service.index_entity(updated)

        # Handle deletions next
        # remove rows from db for files no longer present
        for file_path in changes.deleted:
            await self.handle_entity_deletion(file_path)

        # Parse files that need updating
        parsed_entities: Dict[str, EntityMarkdown] = {}

        for file_path in [*changes.new, *changes.modified]:
            entity_markdown = await self.entity_parser.parse_file(Path(file_path))
            parsed_entities[file_path] = entity_markdown

        # First pass: Create/update entities
        # entities will have a null checksum to indicate they are not complete
        for file_path, entity_markdown in parsed_entities.items():
            # if the file is new, create an entity
            if file_path in changes.new:
                logger.debug(f"Creating new entity_markdown: {file_path}")
                await self.entity_service.create_entity_from_markdown(
                    file_path, entity_markdown
                )
            # otherwise we need to update the entity and observations
            else:
                logger.debug(f"Updating entity_markdown: {file_path}")
                await self.entity_service.update_entity_and_observations(
                    file_path, entity_markdown
                )

        # Second pass
        for file_path, entity_markdown in parsed_entities.items():
            logger.debug(f"Updating relations for: {file_path}")

            # Process relations
            checksum = changes.checksums[file_path]
            entity = await self.entity_service.update_entity_relations(
                file_path, entity_markdown
            )

            # add to search index
            await self.search_service.index_entity(entity)

            # Set final checksum to mark sync complete
            await self.entity_repository.update(entity.id, {"checksum": checksum})

        # Third pass: Try to resolve any forward references
        logger.debug("Attempting to resolve forward references")
        for relation in await self.relation_repository.find_unresolved_relations():
            target_entity = await self.entity_service.link_resolver.resolve_link(relation.to_name)
            # check we found a link that is not the source
            if target_entity and target_entity.id != relation.from_id:
                logger.debug(f"Resolved forward reference: {relation.to_name} -> {target_entity.permalink}")
                await self.relation_repository.update(relation.id, {
                    "to_id": target_entity.id,
                    "to_name": target_entity.title  # Update to actual title
                })

                # update search index
                await self.search_service.index_entity(target_entity)


        return changes
