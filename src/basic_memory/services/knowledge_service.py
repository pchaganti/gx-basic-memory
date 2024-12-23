"""Service for managing knowledge graph entities and their file persistence."""

from pathlib import Path
from typing import Sequence, List

from loguru import logger

from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity as EntitySchema, Relation as RelationSchema
from basic_memory.services.entity_service import EntityService
from basic_memory.services.exceptions import EntityNotFoundError, FileOperationError
from basic_memory.services.file_service import FileService
from basic_memory.services.observation_service import ObservationService
from basic_memory.services.relation_service import RelationService


class KnowledgeService:
    """
    Service for managing knowledge graph entities and their persistence.

    Orchestrates operations between:
    - EntityService for core entity operations
    - ObservationService for atomic facts
    - RelationService for entity connections
    - FileService for persistence
    - KnowledgeParser for file formatting
    """

    def __init__(
        self,
        entity_service: EntityService,
        observation_service: ObservationService,
        relation_service: RelationService,
        file_service: FileService,
        knowledge_writer: KnowledgeWriter,
    ):
        self.entity_service = entity_service
        self.observation_service = observation_service
        self.relation_service = relation_service
        self.file_service = file_service
        self.knowledge_writer = knowledge_writer

    def get_entity_path(self, entity: EntityModel) -> Path:
        """Generate filesystem path for entity."""
        # Store in entities/[type]/[name].md
        return Path("knowledge") / entity.entity_type / f"{entity.name}.md"

    async def write_entity_file(self, entity: EntityModel) -> str:
        """Write entity to filesystem and return checksum."""
        try:
            # Format content
            path = self.get_entity_path(entity)
            entity_content = await self.knowledge_writer.format_content(entity)
            file_content = await self.file_service.add_frontmatter(
                id=entity.id,
                content=entity_content,
                created=entity.created_at,
                updated=entity.updated_at,
            )

            # Write and get checksum
            return await self.file_service.write_file(path, file_content)

        except Exception as e:
            logger.error(f"Failed to write entity file: {e}")
            raise FileOperationError(f"Failed to write entity file: {e}")

    async def create_entity(self, entity: EntitySchema) -> EntityModel:
        """Create a new entity and write to filesystem."""
        logger.debug(f"Creating entity: {entity}")
        try:
            # 1. Create entity in DB
            db_entity = await self.entity_service.create_entity(entity)

            # 2. Write file and get checksum
            checksum = await self.write_entity_file(db_entity)

            # 3. Update DB with checksum
            updated = await self.entity_service.update_entity(db_entity.id, {"checksum": checksum})

            return updated

        except Exception as e:
            # Clean up on any failure
            if "db_entity" in locals():
                await self.entity_service.delete_entity(db_entity.id)  # pyright: ignore [reportPossiblyUnboundVariable]
            if "path" in locals():
                await self.file_service.delete_file(path)  # pyright: ignore [reportUndefinedVariable]  # noqa: F821
            logger.error(f"Failed to create entity: {e}")
            raise

    async def create_entities(self, entities: List[EntitySchema]) -> Sequence[EntityModel]:
        """Create multiple entities."""
        logger.debug(f"Creating {len(entities)} entities")
        created = []

        for entity in entities:
            try:
                created_entity = await self.create_entity(entity)
                created.append(created_entity)
            except Exception as e:
                logger.error(f"Failed to create entity {entity.name}: {e}")
                continue

        return created

    async def create_relations(self, relations: List[RelationSchema]) -> Sequence[RelationSchema]:
        """Create relations and update affected entity files."""
        logger.debug(f"Creating {len(relations)} relations")
        created = []

        for relation in relations:
            try:
                # Create relation in DB
                db_relation = await self.relation_service.create_relation(relation)

                # Get updated entities to write
                from_entity = await self.entity_service.get_entity(relation.from_id)
                to_entity = await self.entity_service.get_entity(relation.to_id)

                # Update files with their new relations
                for entity in [from_entity, to_entity]:
                    checksum = await self.write_entity_file(entity)
                    await self.entity_service.update_entity(entity.id, {"checksum": checksum})

                created.append(db_relation)

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
                continue

        return created

    async def add_observations(
        self, entity_id: int, observations: List[str], context: str | None = None
    ) -> EntityModel:
        """Add observations to entity and update its file."""
        logger.debug(f"Adding observations to entity {entity_id}")

        try:
            # Add observations to DB
            await self.observation_service.add_observations(entity_id, observations, context)

            # Get updated entity
            entity = await self.entity_service.get_entity(entity_id)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {entity_id}")

            # Write updated file
            checksum = await self.write_entity_file(entity)

            # Update checksum in DB
            return await self.entity_service.update_entity(entity_id, {"checksum": checksum})

        except Exception as e:
            logger.error(f"Failed to add observations: {e}")
            raise

    async def delete_entity(self, entity_id: int) -> bool:
        """Delete entity and its file."""
        logger.debug(f"Deleting entity: {entity_id}")

        try:
            # Get entity first for file deletion
            entity = await self.entity_service.get_entity(entity_id)
            if not entity:
                return True  # Already deleted

            # Delete file first (it's source of truth)
            path = self.get_entity_path(entity)
            await self.file_service.delete_file(path)

            # Delete from DB (this will cascade to observations/relations)
            return await self.entity_service.delete_entity(entity_id)

        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            raise

    async def delete_entities(self, entity_ids: List[int]) -> bool:
        """Delete multiple entities and their files."""
        logger.debug(f"Deleting entities: {entity_ids}")
        success = True

        for entity_id in entity_ids:
            try:
                await self.delete_entity(entity_id)
            except Exception as e:
                logger.error(f"Failed to delete entity {entity_id}: {e}")
                success = False
                continue

        return success
