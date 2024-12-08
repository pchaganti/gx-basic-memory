"""Common test fixtures."""
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from basic_memory.models import Base, Entity, Observation, Relation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.deps import (
    get_entity_repo,
    get_observation_repo,
    get_relation_repo,
    get_entity_service,
    get_observation_service,
    get_relation_service,
    get_memory_service
)
from basic_memory.schemas import EntityIn


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create an async engine using in-memory SQLite database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",  # In-memory database
        echo=False  # Set to True for SQL logging
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Create an async session factory and yield a session"""
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def test_project_path():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        yield project_path

@pytest_asyncio.fixture(scope="function")
async def entity_repository(session: AsyncSession):
    """Create an EntityRepository instance"""
    yield EntityRepository(session)


@pytest_asyncio.fixture(scope="function")
async def observation_repository(session: AsyncSession):
    """Create an ObservationRepository instance"""
    return ObservationRepository(session)

@pytest_asyncio.fixture(scope="function")
async def relation_repository(session: AsyncSession):
    """Create a RelationRepository instance"""
    return RelationRepository(session)

@pytest_asyncio.fixture
async def entity_service(test_project_path, entity_repository):
    """Fixture providing initialized EntityService."""
    return await get_entity_service(test_project_path, entity_repository)


@pytest_asyncio.fixture
async def relation_service(test_project_path, relation_repository):
    """Fixture providing initialized RelationService."""
    return await get_relation_service(test_project_path, relation_repository)

@pytest_asyncio.fixture
async def observation_service(test_project_path, observation_repository):
    """Fixture providing initialized RelationService."""
    return await get_observation_service(test_project_path, observation_repository)

@pytest_asyncio.fixture
async def memory_service(
    test_project_path,
    entity_service,
    relation_service,
    observation_service
):
    """Fixture providing initialized MemoryService."""
    return await get_memory_service(
        test_project_path,
        entity_service,
        relation_service,
        observation_service
    )

@pytest_asyncio.fixture(scope="function")
async def sample_entity(entity_repository: EntityRepository):
    """Create a sample entity for testing"""
    entity_data = {
        'id': '20240102-test-entity',
        'name': 'Test Entity',
        'entity_type': 'test',
        'description': 'A test entity',
        'references': 'Test references'
    }
    return await entity_repository.create(entity_data)

@pytest_asyncio.fixture
async def test_entity(entity_service):
    """Create a test entity for reuse in tests."""
    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
    )
    return await entity_service.create_entity(entity_data)