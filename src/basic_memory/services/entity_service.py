"""Service for managing entities in the database."""
from pathlib import Path
from typing import Sequence, List, Optional

import frontmatter
from frontmatter import Post
from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.services.exceptions import EntityNotFoundError, EntityCreationError
from basic_memory.services import FileService
from basic_memory.services import BaseService
from basic_memory.services.link_resolver import LinkResolver
from basic_memory.markdown.entity_parser import EntityParser
from basic_memory.sync import EntitySyncService


class EntityService(BaseService[EntityModel]):
    """Service for managing entities in the database."""

    def __init__(
        self,
        entity_parser: EntityParser,
        entity_sync_service: EntitySyncService,
        entity_repository: EntityRepository,
        file_service: FileService,
        link_resolver: LinkResolver,
    ):
        super().__init__(entity_repository)
        self.entity_parser = entity_parser
        self.entity_sync_service = entity_sync_service
        self.file_service = file_service
        self.link_resolver = link_resolver

    async def create_or_update_entity(self, schema: EntitySchema) -> (EntityModel, bool):
        """Create new entity or update existing one.
        if a new entity is created, the return value is (entity, True)
        """

        logger.debug(f"Creating or updating entity: {schema}")

        # Try to find existing entity using smart resolution
        existing = await self.link_resolver.resolve_link(schema.permalink)

        if existing:
            logger.debug(f"Found existing entity: {existing.permalink}")
            return await self.update_entity(schema), False
        else:
            # Create new entity
            return await self.create_entity(schema), True

    async def create_entity(self, schema: EntitySchema) -> EntityModel:
        """Create a new entity and write to filesystem."""
        logger.debug(f"Creating entity: {schema.permalink}")

        # get file path
        file_path = Path(schema.file_path)

        if await self.file_service.exists(file_path):
            raise EntityCreationError(
                f"file_path {file_path} for entity {schema.permalink} already exists: {file_path}"
            )

        # Convert frontmatter to dict
        frontmatter_dict = schema.entity_metadata or {}
        frontmatter_dict["permalink"] = schema.permalink
        frontmatter_dict["type"] = schema.entity_type
        
        
        # Create Post object for frontmatter
        content = schema.content or ""
        post = Post(content, **frontmatter_dict)

        # write file
        final_content = frontmatter.dumps(post)
        checksum = await self.file_service.write_file(file_path, final_content)

        # parse entity from file
        entity_markdown = await self.entity_parser.parse_file(file_path)
        created_entity = await self.entity_sync_service.create_entity_from_markdown(file_path, entity_markdown)

        # add relations
        entity = await self.entity_sync_service.update_entity_relations(file_path, entity_markdown)

        # Set final checksum to mark complete
        return await self.repository.update(entity.id, {"checksum": checksum})

    async def update_entity(self, schema: EntitySchema) -> EntityModel:
        """Update an entity's content and metadata."""
        logger.debug(f"Updating entity with permalink: {schema.permalink}")

        # get file path
        file_path = Path(schema.file_path)

        # Convert frontmatter to dict
        frontmatter_dict = schema.entity_metadata or {}
        frontmatter_dict["permalink"] = schema.permalink
        frontmatter_dict["type"] = schema.entity_type

        # Create Post object for frontmatter
        content = schema.content or ""
        post = Post(content, **frontmatter_dict)

        # write file
        final_content = frontmatter.dumps(post)
        checksum = await self.file_service.write_file(file_path, final_content)

        # parse entity from file
        entity_markdown = await self.entity_parser.parse_file(file_path)

        # update entity in db
        entity = await self.entity_sync_service.update_entity_and_observations(
            file_path, entity_markdown
        )

        # add relations
        await self.entity_sync_service.update_entity_relations(file_path, entity_markdown)

        # Set final checksum to match file
        entity = await self.repository.update(entity.id, {"checksum": checksum})

        return entity

    async def delete_entity(self, permalink: str) -> bool:
        """Delete entity and its file."""
        logger.debug(f"Deleting entity: {permalink}")

        try:
            # Get entity first for file deletion
            entity = await self.get_by_permalink(permalink)

            # Delete file first
            await self.file_service.delete_entity_file(entity)

            # Delete from DB (this will cascade to observations/relations)
            return await self.repository.delete(entity.id)

        except EntityNotFoundError:
            logger.info(f"Entity not found: {permalink}")
            return True  # Already deleted

        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            raise

    async def get_by_permalink(self, permalink: str) -> EntityModel:
        """Get entity by type and name combination."""
        logger.debug(f"Getting entity by permalink: {permalink}")
        db_entity = await self.repository.get_by_permalink(permalink)
        if not db_entity:
            raise EntityNotFoundError(f"Entity not found: {permalink}")
        return db_entity

    async def get_all(self) -> Sequence[EntityModel]:
        """Get all entities."""
        return await self.repository.find_all()

    async def get_entity_types(self) -> List[str]:
        """Get list of all distinct entity types in the system."""
        logger.debug("Getting all distinct entity types")
        return await self.repository.get_entity_types()

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        sort_by: Optional[str] = "updated_at",
        include_related: bool = False,
    ) -> Sequence[EntityModel]:
        """List entities with optional filtering and sorting."""
        logger.debug(f"Listing entities: type={entity_type} sort={sort_by}")
        return await self.repository.list_entities(entity_type=entity_type, sort_by=sort_by)

    async def get_entities_by_permalinks(self, permalinks: List[str]) -> Sequence[EntityModel]:
        """Get specific nodes and their relationships."""
        logger.debug(f"Getting entities permalinks: {permalinks}")
        return await self.repository.find_by_permalinks(permalinks)

    async def delete_entity_by_file_path(self, file_path):
        await self.repository.delete_by_file_path(file_path)
