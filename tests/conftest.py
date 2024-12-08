"""Common test fixtures for basic-memory."""
import pytest_asyncio
from pathlib import Path
import tempfile

from basic_memory.db import DatabaseType, get_database_url, init_database, get_session, dispose_database
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
    """Create an async engine using in-memory SQLite database."""
    url = get_database_url(DatabaseType.MEMORY)
    engine = await init_database(url)
    try:
        yield engine
    finally:
        await dispose_database(engine)

@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Create a database session with proper lifecycle management."""
    async with get_session(engine) as session:
        yield session

@pytest_asyncio.fixture
async def test_project_path():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        yield project_path

@pytest_asyncio.fixture
async def entity_repo(session):
    """Create an EntityRepository instance."""
    return await get_entity_repo(session)

@pytest_asyncio.fixture
async def observation_repo(session):
    """Create an ObservationRepository instance."""
    return await get_observation_repo(session)

@pytest_asyncio.fixture
async def relation_repo(session):
    """Create a RelationRepository instance."""
    return await get_relation_repo(session)

@pytest_asyncio.fixture
async def entity_service(test_project_path, entity_repo):
    """Fixture providing initialized EntityService."""
    return await get_entity_service(test_project_path, entity_repo)

@pytest_asyncio.fixture
async def observation_service(test_project_path, observation_repo):
    """Fixture providing initialized ObservationService."""
    return await get_observation_service(test_project_path, observation_repo)

@pytest_asyncio.fixture
async def relation_service(test_project_path, relation_repo):
    """Fixture providing initialized RelationService."""
    return await get_relation_service(test_project_path, relation_repo)

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

@pytest_asyncio.fixture
async def test_entity(entity_service):
    """Create a test entity for reuse in tests."""
    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
    )
    return await entity_service.create_entity(entity_data)