"""Service for syncing files between filesystem and database."""

import mimetypes
from pathlib import Path
from typing import Tuple

import logfire
from loguru import logger
from sqlalchemy.exc import IntegrityError

from basic_memory import file_utils
from basic_memory.markdown import EntityParser
from basic_memory.repository import EntityRepository, RelationRepository
from basic_memory.services import EntityService, FileService
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.utils import SyncReport
from basic_memory.models import Entity


class SyncService:
    """Syncs documents and knowledge files with database."""

    def __init__(
        self,
        scanner: FileChangeScanner,
        entity_service: EntityService,
        entity_parser: EntityParser,
        entity_repository: EntityRepository,
        relation_repository: RelationRepository,
        search_service: SearchService,
        file_service: FileService,
    ):
        self.scanner = scanner
        self.entity_service = entity_service
        self.entity_parser = entity_parser
        self.entity_repository = entity_repository
        self.relation_repository = relation_repository
        self.search_service = search_service
        self.file_service = file_service

    async def sync_file(self, path: str) -> Tuple[Entity, str]:
        """Sync a single file completely."""

        try:
            if self.file_service.is_markdown(path):
                entity, checksum = await self.sync_markdown_file(path)
            else:
                entity, checksum = await self.sync_regular_file(path)
            await self.search_service.index_entity(entity)
            return entity, checksum

        except Exception as e:
            logger.error(f"Failed to sync {path}: {e}")
            raise

    async def sync_markdown_file(self, path: str) -> Tuple[Entity, str]:
        """Sync a markdown file with full processing."""

        # Parse markdown first to get any existing permalink
        entity_markdown = await self.entity_parser.parse_file(path)

        # Resolve permalink - this handles all the cases including conflicts
        permalink = await self.entity_service.resolve_permalink(path, markdown=entity_markdown)

        # If permalink changed, update the file
        if permalink != entity_markdown.frontmatter.permalink:
            logger.info(f"Updating permalink in {path}: {permalink}")
            entity_markdown.frontmatter.metadata["permalink"] = permalink
            checksum = await self.file_service.update_frontmatter(path, {"permalink": permalink})
        else:
            checksum = await self.file_service.compute_checksum(path)

        # Create/update entity with resolved permalink
        entity = await self.entity_service.create_entity_from_markdown(path, entity_markdown)

        # Update relations and search index
        entity = await self.entity_service.update_entity_relations(path, entity_markdown)

        return entity, checksum

    async def sync_regular_file(self, path: Path) -> Tuple[Entity, str]:
        """Sync a non-markdown file with basic tracking."""

        checksum = await self.file_service.compute_checksum(path)
        existing = await self.entity_repository.get_by_file_path(path)
        if not existing:
            # Generate permalink from path
            permalink = await self.entity_service.resolve_permalink(path)

            # get file timestamps
            file_stats = self.file_service.file_stats(path)

            # get mime type
            mime_type, _ = mimetypes.guess_type(path.name)
            content_type = mime_type or "text/plain"

            entity = await self.entity_repository.add(
                Entity(
                    entity_type="file",
                    file_path=path,
                    permalink=permalink,
                    checksum=checksum,
                    title=path.name,
                    created_at=file_stats.st_ctime,
                    updated_at=file_stats.st_mtime,
                    content_type=content_type,
                )
            )
        else:
            entity = await self.entity_repository.update(
                existing.id, {"file_path": path, "checksum": checksum}
            )

        await self.search_service.index_entity(entity)
        return entity, checksum

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

    async def sync(self, directory: Path) -> SyncReport:
        """Sync all files with database."""

        with logfire.span("sync", directory=directory):
            changes = await self.scanner.find_knowledge_changes(directory)
            logger.info(f"Found {changes.total_changes} knowledge changes")

            # Handle moves first
            for old_path, new_path in changes.moves.items():
                logger.debug(f"Moving entity: {old_path} -> {new_path}")
                entity = await self.entity_repository.get_by_file_path(old_path)
                if entity:
                    # Update file_path but keep the same permalink for link stability
                    await self.entity_repository.update(
                        entity.id, {"file_path": new_path, "checksum": changes.checksums[new_path]}
                    )
                    # update search index
                    await self.search_service.index_entity(entity)

            # Handle deletions next
            for path in changes.deleted:
                await self.handle_entity_deletion(path)

            # Handle new and modified files
            for path in [*changes.new, *changes.modified]:
                logger.debug(f"Syncing file: {path}")
                entity, checksum = await self.sync_file(path)
                changes.checksums[path] = checksum

            await self.resolve_relations()
            return changes

    async def resolve_relations(self):
        """Try to resolve any unresolved relations"""

        logger.debug("Attempting to resolve forward references")
        for relation in await self.relation_repository.find_unresolved_relations():
            resolved_entity = await self.entity_service.link_resolver.resolve_link(relation.to_name)

            # ignore reference to self
            if resolved_entity and resolved_entity.id != relation.from_id:
                logger.debug(
                    f"Resolved forward reference: {relation.to_name} -> {resolved_entity.title}"
                )
                try:
                    await self.relation_repository.update(
                        relation.id,
                        {
                            "to_id": resolved_entity.id,
                            "to_name": resolved_entity.title,
                        },
                    )
                except IntegrityError:
                    logger.debug(f"Ignoring duplicate relation {relation}")

                # update search index
                await self.search_service.index_entity(resolved_entity)
