"""Common test fixtures."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.db import DatabaseType
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.markdown.knowledge_parser import KnowledgeParser
from basic_memory.models import Base
from basic_memory.models.knowledge import Entity
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.services import (
    EntityService,
    ObservationService,
    RelationService,
    DocumentService,
    FileChangeScanner,
)
from basic_memory.services.file_service import FileService
from basic_memory.services import KnowledgeService


@pytest_asyncio.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
def test_config(tmp_path):
    """Test configuration using in-memory DB."""
    config = ProjectConfig(
        name="test",
    )
    config.home = tmp_path
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
) -> DocumentService:
    """Create a DocumentService instance."""
    return DocumentService(document_repository, test_config.documents_dir)


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
def file_sync_service(document_repository, entity_repository) -> FileChangeScanner:
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