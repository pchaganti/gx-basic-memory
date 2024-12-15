"""Common test fixtures."""
import tempfile
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from basic_memory import db
from basic_memory.db import DatabaseType
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.deps import (
    get_entity_service,
    get_observation_service,
    get_relation_service,
    get_relation_repo, get_observation_repo, get_entity_repo
)
from basic_memory.schemas import EntityIn
from basic_memory.config import ProjectConfig
from basic_memory.services import MemoryService


@pytest_asyncio.fixture
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture
def test_config(tmp_path):
    """Test configuration using in-memory DB."""
    config = ProjectConfig(
        name="test",
    )
    config.path=tmp_path
    return config


@pytest_asyncio.fixture(scope="function")
async def engine(test_config):
    """Create an async engine using in-memory SQLite database"""
    async with db.engine(project_path=test_config.path, db_type=DatabaseType.MEMORY) as engine:
        yield engine


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
    return await get_entity_repo(session)

@pytest_asyncio.fixture(scope="function")
async def observation_repository(session: AsyncSession):
    """Create an ObservationRepository instance"""
    return await get_observation_repo(session)

@pytest_asyncio.fixture(scope="function")
async def relation_repository(session: AsyncSession):
    """Create a RelationRepository instance"""
    return await get_relation_repo(session)

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
    return MemoryService(
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
    }
    return await entity_repository.create(entity_data)

@pytest_asyncio.fixture
async def test_entity(entity_service):
    """Create a test entity for reuse in tests."""
    entity_data = EntityIn(  # pyright: ignore [reportCallIssue]
        name="Test Entity",
        entity_type="test",  # pyright: ignore [reportCallIssue]
    )
    return await entity_service.create_entity(entity_data)

# Test data fixtures
@pytest_asyncio.fixture
def test_entity_data():
    """Sample data for creating a test entity using camelCase (like MCP will)."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entityType": "test",
            "description": "",  # Empty string instead of None
            "observations": [{"content": "This is a test observation"}]
        }]
    }

@pytest_asyncio.fixture
def test_entity_snake_case():
    """Same test data but using snake_case to test schema flexibility."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test",
            "description": "",  # Empty string instead of None
            "observations": [{"content": "This is a test observation"}]
        }]
    }
