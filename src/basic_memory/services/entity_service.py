"""Service for managing entities in the database."""

from typing import Dict, Any, Sequence, List, Optional

from loguru import logger

from basic_memory.models import Entity as EntityModel, Observation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.services.exceptions import EntityNotFoundError
from . import FileService
from . import BaseService


def entity_model(entity: EntitySchema):
    model = EntityModel(
        title=entity.title,
        entity_type=entity.entity_type,
        entity_metadata=entity.entity_metadata,
        permalink=entity.permalink,
        file_path=entity.file_path,
        summary=entity.summary,
        content_type=entity.content_type,
        observations=[Observation(content=observation) for observation in entity.observations],
    )
    return model


class EntityService(BaseService[EntityModel]):
    """Service for managing entities in the database."""

    def __init__(self, entity_repository: EntityRepository, file_service: FileService):
        super().__init__(entity_repository)
        self.file_service = file_service

    async def create_entity(self, schema: EntitySchema) -> EntityModel:
        """Create a new entity and write to filesystem."""
        logger.debug(f"Creating entity: {schema}")

        db_entity = None
        try:
            # 1. Create entity in DB
            model = entity_model(schema)
            db_entity = await self.repository.add(model)

            # if content is provided use that, otherwise write the entity info
            content = schema.content or None

            # 2. Write file and get checksum
            _, checksum = await self.file_service.write_entity_file(db_entity, content=content)

            # 3. Update DB with checksum
            updated = await self.repository.update(db_entity.id, {"checksum": checksum})

            return updated

        except Exception as e:
            # Clean up on any failure
            if db_entity:
                await self.delete_entity(db_entity.permalink)
                await self.file_service.delete_entity_file(db_entity)
            logger.error(f"Failed to create entity: {e}")
            raise

    async def create_entities(self, entities: List[EntitySchema]) -> Sequence[EntityModel]:
        """Create multiple entities."""
        logger.debug(f"Creating {len(entities)} entities")
        return [await self.create_entity(entity) for entity in entities]

    async def update_entity(
        self,
        permalink: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **update_fields: Any,
    ) -> EntityModel:
        """Update an entity's content and metadata.

        Args:
            permalink: Entity's path ID
            content: Optional new content
            metadata: Optional metadata updates
            **update_fields: Additional entity fields to update

        Returns:
            Updated entity

        Raises:
            EntityNotFoundError: If entity doesn't exist
        """
        logger.debug(f"Updating entity with permalink: {permalink}")

        # Get existing entity
        entity = await self.get_by_permalink(permalink)
        if not entity:
            raise EntityNotFoundError(f"Entity not found: {permalink}")

        try:
            # Build update data
            update_data = {}

            # Add any direct field updates
            if update_fields:
                update_data.update(update_fields)

            # Handle metadata update
            if metadata is not None:
                # Update existing metadata
                new_metadata = dict(entity.entity_metadata or {})
                new_metadata.update(metadata)
                update_data["entity_metadata"] = new_metadata

            # Update entity in database if we have changes
            if update_data:
                entity = await self.repository.update(entity.id, update_data)

            # Always write file if we have any updates
            if update_data or content is not None:
                _, checksum = await self.file_service.write_entity_file(
                    entity=entity, content=content
                )
                # Update checksum in DB
                entity = await self.repository.update(entity.id, {"checksum": checksum})

            return entity

        except Exception as e:
            logger.error(f"Failed to update entity: {e}")
            raise

    async def delete_entity(self, permalink: str) -> bool:
        """Delete entity and its file."""
        logger.debug(f"Deleting entity: {permalink}")

        try:
            # Get entity first for file deletion
            entity = await self.get_by_permalink(permalink)

            # Delete file first (it's source of truth)
            await self.file_service.delete_entity_file(entity)

            # Delete from DB (this will cascade to observations/relations)
            return await self.repository.delete(entity.id)

        except EntityNotFoundError:
            logger.info(f"Entity not found: {permalink}")
            return True  # Already deleted

        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            raise

    async def delete_entities(self, permalinks: List[str]) -> bool:
        """Delete multiple entities and their files."""
        logger.debug(f"Deleting entities: {permalinks}")
        success = True

        for permalink in permalinks:
            await self.delete_entity(permalink)
            success = True

        return success

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

    async def open_nodes(self, permalinks: List[str]) -> Sequence[EntityModel]:
        """Get specific nodes and their relationships."""
        logger.debug(f"Opening nodes permalinks: {permalinks}")
        return await self.repository.find_by_permalinks(permalinks)

    async def delete_entity_by_file_path(self, file_path):
        await self.repository.delete_by_file_path(file_path)
