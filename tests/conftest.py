"""Common test fixtures."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.db import DatabaseType
from basic_memory.markdown import EntityParser
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Base
from basic_memory.models.knowledge import Entity
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.services import (
    EntityService,
    ObservationService,
    RelationService,
)
from basic_memory.services.activity_service import ActivityService
from basic_memory.services.file_service import FileService
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.entity_sync_service import EntitySyncService
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

    (tmp_path / config.home.name).mkdir(parents=True, exist_ok=True)
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
async def entity_service(
    entity_repository: EntityRepository, file_service: FileService
) -> EntityService:
    """Create EntityService with repository."""
    return EntityService(entity_repository=entity_repository, file_service=file_service)


@pytest_asyncio.fixture
async def relation_service(
    relation_repository: RelationRepository,
    entity_repository: EntityRepository,
    file_service: FileService,
) -> RelationService:
    """Create RelationService with repository."""
    return RelationService(
        relation_repository=relation_repository,
        entity_repository=entity_repository,
        file_service=file_service,
    )


@pytest_asyncio.fixture
async def observation_service(
    observation_repository: ObservationRepository,
    entity_repository: EntityRepository,
    file_service: FileService,
) -> ObservationService:
    """Create ObservationService with repository."""
    return ObservationService(observation_repository, entity_repository, file_service)


@pytest.fixture
def file_service(test_config: ProjectConfig, knowledge_writer: KnowledgeWriter) -> FileService:
    """Create FileService instance."""
    return FileService(test_config.home, knowledge_writer)


@pytest.fixture
def knowledge_writer():
    """Create writer instance."""
    return KnowledgeWriter()


@pytest.fixture
def entity_parser(test_config):
    """Create parser instance."""
    return EntityParser(test_config.home)


@pytest_asyncio.fixture
def file_change_scanner(entity_repository) -> FileChangeScanner:
    """Create FileChangeScanner instance."""
    return FileChangeScanner(entity_repository)


@pytest_asyncio.fixture
async def activity_service(document_service, entity_service, relation_service):
    """Create activity service with real dependencies."""
    return ActivityService(entity_service, document_service, relation_service)


@pytest_asyncio.fixture
async def knowledge_sync_service(
    entity_repository: EntityRepository,
    observation_repository: ObservationRepository,
    relation_repository: RelationRepository,
) -> EntitySyncService:
    """Create EntitySyncService with repository."""
    return EntitySyncService(entity_repository, observation_repository, relation_repository)


@pytest_asyncio.fixture
async def sync_service(
    knowledge_sync_service: EntitySyncService,
    file_change_scanner: FileChangeScanner,
    entity_parser: EntityParser,
    search_service: SearchService,
) -> SyncService:
    """Create sync service for testing."""
    return SyncService(
        scanner=file_change_scanner,
        entity_sync_service=knowledge_sync_service,
        entity_parser=entity_parser,
        search_service=search_service,
    )


@pytest_asyncio.fixture
async def search_repository(session_maker):
    """Create SearchRepository instance"""
    return SearchRepository(session_maker)


@pytest_asyncio.fixture(autouse=True)
async def init_search_index(search_service):
    await search_service.init_search_index()


@pytest_asyncio.fixture
async def search_service(
    search_repository: SearchRepository,
    entity_repository: EntityRepository,
) -> SearchService:
    """Create and initialize search service"""
    service = SearchService(search_repository, entity_repository)
    await service.init_search_index()
    return service


@pytest_asyncio.fixture(scope="function")
async def sample_entity(entity_repository: EntityRepository) -> Entity:
    """Create a sample entity for testing."""
    entity_data = {
        "name": "Test Entity",
        "entity_type": "test",
        "summary": "A test entity",
        "path_id": "test/test_entity",
        "file_path": "test/test_entity.md",
        "content_type": "text/markdown",
    }
    return await entity_repository.create(entity_data)
