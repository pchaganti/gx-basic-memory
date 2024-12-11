"""Common test fixtures."""
import tempfile
from pathlib import Path

import pytest_asyncio
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from basic_memory.models import Base
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.deps import (
    get_entity_service,
    get_observation_service,
    get_relation_service,
    get_memory_service
)
from basic_memory.schemas import EntityIn
from basic_memory.debug_utils import dump_db_state
from basic_memory.config import ProjectConfig

@pytest_asyncio.fixture
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture
def test_config():
    """Test configuration using in-memory DB."""
    return ProjectConfig(
        name="test",
        database_url="sqlite+aiosqlite:///:memory:",
        path=Path("/tmp/basic-memory-test")  # Will be created and validated
    )

@pytest_asyncio.fixture(scope="function")
async def engine(test_config):
    """Create an async engine using in-memory SQLite database"""
    logger.info(f"Creating new in-memory SQLite database at {test_config.database_url}")
    engine = create_async_engine(
        test_config.database_url,
        echo=True  # SQL logging
    )
    logger.debug(f"engine url: {engine.url}")

    # Debug: Show empty state before anything is created
    await dump_db_state(engine)

    try:
        # Establish connection and create tables
        async with engine.begin() as conn:
            # For paranoia, try to drop anything that might exist
            logger.info("Attempting to drop any existing tables...")
            try:
                await conn.run_sync(Base.metadata.drop_all)
            except Exception as e:
                logger.warning(f"Drop tables failed (this is usually ok): {e}")
                
            # Verify clean state
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
            ))
            table_count = result.scalar()
            logger.info(f"Tables in clean database: {table_count}")
            
            # Create fresh tables
            logger.info("Creating tables from SQLAlchemy models...")
            await conn.run_sync(Base.metadata.create_all)
            
            # Verify table creation
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ))
            tables = result.fetchall()
            logger.info("Created tables:")
            for table in tables:
                logger.info(f"  {table[0]}")

        # Debug: Show final state after creation
        await dump_db_state(engine)

        yield engine
    except Exception as e:
        logger.error(f"Error during test database setup: {e}")
        raise
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
    yield ObservationRepository(session)

@pytest_asyncio.fixture(scope="function")
async def relation_repository(session: AsyncSession):
    """Create a RelationRepository instance"""
    yield RelationRepository(session)

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
