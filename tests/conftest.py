"""Common test fixtures."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.db import DatabaseType
from basic_memory.models import Base, Entity as EntityModel
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.schemas import Entity
from basic_memory.services import (
    EntityService,
    ObservationService,
    RelationService,
)


@pytest_asyncio.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
def test_config(tmp_path):
    """Test configuration using in-memory DB."""
    config = ProjectConfig(
        name="test",
    )
    config.path = tmp_path
    return config


@pytest_asyncio.fixture(scope="function")
async def engine_factory(
    test_config,
) -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    """Create engine and session factory using in-memory SQLite database."""
    async with db.engine_session_factory(
        project_path=test_config.path, db_type=DatabaseType.MEMORY
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


@pytest_asyncio.fixture
async def test_project_path():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        yield project_path


@pytest_asyncio.fixture(scope="function")
async def document_repository(session_maker: async_sessionmaker[AsyncSession]) -> DocumentRepository:
    """Create a DocumentRepository instance."""
    return DocumentRepository(session_maker)


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
    return EntityService(entity_repository)


@pytest_asyncio.fixture
async def relation_service(relation_repository: RelationRepository) -> RelationService:
    """Create RelationService with repository."""
    return RelationService(relation_repository)


@pytest_asyncio.fixture
async def observation_service(observation_repository: ObservationRepository) -> ObservationService:
    """Create ObservationService with repository."""
    return ObservationService(observation_repository)


@pytest_asyncio.fixture(scope="function")
async def sample_entity(entity_repository: EntityRepository) -> EntityModel:
    """Create a sample entity for testing."""
    entity_data = {
        "id": "test/test_entity",
        "name": "Test Entity",
        "entity_type": "test",
        "description": "A test entity",
    }
    return await entity_repository.create(entity_data)


@pytest_asyncio.fixture
async def test_entity(entity_service: EntityService) -> EntityModel:
    """Create a test entity for reuse in tests."""
    entity_data = Entity(name="Test Entity", entity_type="test", observations=[])
    return await entity_service.create_entity(entity_data)