"""Main knowledge service implementation."""

from pathlib import Path
from typing import List, Sequence, Tuple, Dict, Any, Optional


from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.schemas import Relation as RelationSchema
from basic_memory.schemas.request import ObservationCreate
from basic_memory.services.entity_service import EntityService
from basic_memory.services.file_service import FileService
from basic_memory.services.observation_service import ObservationService
from basic_memory.services.relation_service import RelationService

from .file_operations import FileOperations
from .entity_operations import EntityOperations
from .relation_operations import RelationOperations
from .observation_operations import ObservationOperations


class KnowledgeService:
    """
    Service for managing knowledge graph entities and their persistence.

    Composes specialized operations for:
    - File handling and persistence
    - Entity CRUD operations
    - Relations between entities
    - Observations about entities

    Acts as the main coordinator for all knowledge operations, ensuring
    consistency between database and filesystem.
    """

    def __init__(
        self,
        entity_service: EntityService,
        observation_service: ObservationService,
        relation_service: RelationService,
        file_service: FileService,
        knowledge_writer: KnowledgeWriter,
        base_path: Path,
    ):
        self.base_path = base_path

        # Initialize operations in dependency order
        self.file_ops = FileOperations(
            entity_service=entity_service,
            file_service=file_service,
            knowledge_writer=knowledge_writer,
            base_path=base_path,
        )

        self.entity_ops = EntityOperations(
            entity_service=entity_service, file_operations=self.file_ops
        )

        self.relation_ops = RelationOperations(
            relation_service=relation_service,
            entity_service=entity_service,
            file_operations=self.file_ops,
        )

        self.observation_ops = ObservationOperations(
            observation_service=observation_service,
            entity_service=entity_service,
            file_operations=self.file_ops,
        )

    # Entity operations
    async def get_entity_by_path_id(self, path_id: str) -> EntityModel:
        return await self.entity_ops.get_by_path_id(path_id)

    async def read_entity_content(self, entity: EntityModel) -> str:
        return await self.entity_ops.read_entity_content(entity)

    async def create_entity(self, entity: EntitySchema) -> EntityModel:
        """Create a new entity."""
        return await self.entity_ops.create_entity(entity)

    async def create_entities(self, entities: List[EntitySchema]) -> Sequence[EntityModel]:
        """Create multiple entities."""
        return await self.entity_ops.create_entities(entities)

    async def update_entity(
        self,
        path_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **update_fields: Any,
    ) -> EntityModel:
        """Update an entity's content and metadata.

        Args:
            path_id: Entity's path ID
            content: Optional new content
            metadata: Optional metadata updates
            **update_fields: Additional entity fields to update

        Returns:
            Updated entity
        """
        return await self.entity_ops.update_entity(
            path_id=path_id, content=content, metadata=metadata, **update_fields
        )

    async def delete_entity(self, path_id: str) -> bool:
        """Delete an entity and its file."""
        return await self.entity_ops.delete_entity(path_id)

    async def delete_entities(self, path_ids: List[str]) -> bool:
        """Delete multiple entities and their files."""
        return await self.entity_ops.delete_entities(path_ids)

    async def file_exists(self, path: Path) -> bool:
        """Check if entity file exists."""
        return await self.file_ops.file_exists(path)

    async def read_file(self, path: Path) -> Tuple[str, str]:
        """Check if entity file exists."""
        return await self.file_ops.read_file(path)

    # Relation operations
    async def create_relations(self, relations: List[RelationSchema]) -> Sequence[EntityModel]:
        """Create relations between entities."""
        return await self.relation_ops.create_relations(relations)

    async def delete_relations(self, to_delete: List[RelationSchema]) -> Sequence[EntityModel]:
        """Delete relations between entities."""
        return await self.relation_ops.delete_relations(to_delete)

    # Observation operations
    async def add_observations(
        self, path_id: str, observations: List[ObservationCreate], context: str | None = None
    ) -> EntityModel:
        """Add observations to an entity."""
        return await self.observation_ops.add_observations(path_id, observations, context)

    async def delete_observations(self, path_id: str, observations: List[str]) -> EntityModel:
        """Delete observations from an entity."""
        return await self.observation_ops.delete_observations(path_id, observations)

    # File operations for direct access if needed
    def get_entity_path(self, entity: EntityModel) -> Path:
        """Get filesystem path for entity."""
        return self.file_ops.get_entity_path(entity)

    async def write_entity_file(self, entity: EntityModel) -> Path:
        """Write entity to filesystem."""
        path, _ = await self.file_ops.write_entity_file(entity)
        return path
