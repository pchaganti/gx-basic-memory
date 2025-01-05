"""Common test fixtures."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.db import DatabaseType
from basic_memory.markdown.knowledge_parser import KnowledgeParser
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Base
from basic_memory.models.knowledge import Entity
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.services import (
    EntityService,
    ObservationService,
    RelationService,
    DocumentService,
)
from basic_memory.services import KnowledgeService
from basic_memory.services.activity_service import ActivityService
from basic_memory.services.file_service import FileService
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.knowledge_sync_service import KnowledgeSyncService
from basic_memory.sync.sync_service import SyncService


@pytest_asyncio.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
def test_config(tmp_path) -> ProjectConfig:
    """Test configuration using in-memory DB."""
    config = ProjectConfig(
        name="test",
    )
    config.home = tmp_path

    (tmp_path / config.documents_dir.name).mkdir(parents=True, exist_ok=True)
    (tmp_path / config.knowledge_dir.name).mkdir(parents=True, exist_ok=True)
    return config


@pytest_asyncio.fixture(scope="function")
async def engine_factory(
    test_config,
) -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    """Create engine and session factory using in-memory SQLite database."""
    async with db.engine_session_factory(
        db_path=test_config.database_path, db_type=DatabaseType.MEMORY
    ) as (engine, session_maker):
        # Initialize database
        async with db.scoped_session(session_maker) as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))
            conn = await session.connection()
            await conn.run_sync(Base.metadata.create_all)

        yield engine, session_maker


@pytest_asyncio.fixture
async def session_maker(engine_factory) -> async_sessionmaker[AsyncSession]:
    """Get session maker for tests."""
    _, session_maker = engine_factory
    return session_maker


@pytest_asyncio.fixture(scope="function")
async def document_repository(
    session_maker: async_sessionmaker[AsyncSession],
) -> DocumentRepository:
    """Create a DocumentRepository instance."""
    return DocumentRepository(session_maker)


@pytest_asyncio.fixture(scope="function")
async def document_service(
    document_repository: DocumentRepository,
    test_config: ProjectConfig,
    file_service: FileService,
) -> DocumentService:
    """Create a DocumentService instance."""
    return DocumentService(document_repository, test_config.documents_dir, file_service)


@pytest_asyncio.fixture(scope="function")
async def entity_repository(session_maker: async_sessionmaker[AsyncSession]) -> EntityRepository:
    """Create an EntityRepository instance."""
    return EntityRepository(session_maker)


@pytest_asyncio.fixture(scope="function")
async def observation_repository(
    session_maker: async_sessionmaker[AsyncSession],
) -> ObservationRepository:
    """Create an ObservationRepository instance."""
    return ObservationRepository(session_maker)


@pytest_asyncio.fixture(scope="function")
async def relation_repository(
    session_maker: async_sessionmaker[AsyncSession],
) -> RelationRepository:
    """Create a RelationRepository instance."""
    return RelationRepository(session_maker)


@pytest_asyncio.fixture
async def entity_service(entity_repository: EntityRepository) -> EntityService:
    """Create EntityService with repository."""
    return EntityService(entity_repository=entity_repository)


@pytest_asyncio.fixture
async def relation_service(relation_repository: RelationRepository) -> RelationService:
    """Create RelationService with repository."""
    return RelationService(relation_repository=relation_repository)


@pytest_asyncio.fixture
async def observation_service(
    observation_repository: ObservationRepository,
    entity_service: EntityService,
) -> ObservationService:
    """Create ObservationService with repository."""
    return ObservationService(observation_repository)


@pytest.fixture
def file_service():
    """Create FileService instance."""
    return FileService()


@pytest.fixture
def knowledge_writer():
    """Create writer instance."""
    return KnowledgeWriter()


@pytest.fixture
def knowledge_parser():
    """Create parser instance."""
    return KnowledgeParser()


@pytest_asyncio.fixture
def file_change_scanner(document_repository, entity_repository) -> FileChangeScanner:
    """Create FileChangeScanner instance."""
    return FileChangeScanner(document_repository, entity_repository)


@pytest_asyncio.fixture
async def knowledge_service(
    entity_service: EntityService,
    observation_service: ObservationService,
    relation_service: RelationService,
    file_service: FileService,
    knowledge_writer: KnowledgeWriter,
    test_config: ProjectConfig,
) -> KnowledgeService:
    """Create KnowledgeService with dependencies."""
    return KnowledgeService(
        entity_service=entity_service,
        observation_service=observation_service,
        relation_service=relation_service,
        file_service=file_service,
        knowledge_writer=knowledge_writer,
        base_path=test_config.knowledge_dir,
    )


@pytest_asyncio.fixture
async def activity_service(document_service, entity_service, relation_service):
    """Create activity service with real dependencies."""
    return ActivityService(entity_service, document_service, relation_service)


@pytest_asyncio.fixture
async def knowledge_sync_service(
    entity_service: EntityService,
    observation_service: ObservationService,
    relation_service: RelationService,
) -> KnowledgeSyncService:
    """Create EntitySyncService with repository."""
    return KnowledgeSyncService(entity_service, observation_service, relation_service)


@pytest_asyncio.fixture
async def sync_service(
    document_service: DocumentService,
    knowledge_sync_service: KnowledgeSyncService,
    file_change_scanner: FileChangeScanner,
    knowledge_parser: KnowledgeParser,
) -> SyncService:
    """Create sync service for testing."""
    return SyncService(
        scanner=file_change_scanner,
        document_service=document_service,
        knowledge_sync_service=knowledge_sync_service,
        knowledge_parser=knowledge_parser,
    )


@pytest_asyncio.fixture
async def search_repository(session_maker):
    """Create SearchRepository instance"""
    return SearchRepository(session_maker)


@pytest_asyncio.fixture
async def search_service(
    search_repository: SearchRepository,
    entity_service: EntityService,
    document_service: DocumentService,
) -> SearchService:
    """Create and initialize search service"""
    service = SearchService(search_repository, document_service, entity_service)
    await service.init_search_index()
    return service


@pytest_asyncio.fixture(scope="function")
async def sample_entity(entity_repository: EntityRepository) -> Entity:
    """Create a sample entity for testing."""
    entity_data = {
        "name": "Test Entity",
        "entity_type": "test",
        "description": "A test entity",
        "path_id": "test/test_entity",
        "file_path": "test/test_entity.md",
    }
    return await entity_repository.create(entity_data)
