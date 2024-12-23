"""Main knowledge service implementation."""

from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.services.entity_service import EntityService
from basic_memory.services.file_service import FileService
from basic_memory.services.observation_service import ObservationService
from basic_memory.services.relation_service import RelationService
from .observations import ObservationOperations


class KnowledgeService(ObservationOperations):
    """
    Service for managing knowledge graph entities and their persistence.

    Orchestrates operations between:
    - EntityService for core entity operations
    - ObservationService for atomic facts
    - RelationService for entity connections
    - FileService for persistence
    - KnowledgeParser for file formatting

    Operations are split across mixins:
    - FileOperations: Core file handling
    - EntityOperations: Entity CRUD operations
    - RelationOperations: Relation management
    - ObservationOperations: Observation handling
    """

    def __init__(
        self,
        entity_service: EntityService,
        observation_service: ObservationService,
        relation_service: RelationService,
        file_service: FileService,
        knowledge_writer: KnowledgeWriter,
    ):
        super().__init__(
            entity_service=entity_service,
            observation_service=observation_service,
            relation_service=relation_service,
            file_service=file_service,
            knowledge_writer=knowledge_writer,
        )