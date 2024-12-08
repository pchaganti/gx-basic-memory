"""Common test fixtures for basic-memory."""
import pytest_asyncio
from pathlib import Path
import tempfile
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from basic_memory.models import Base
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
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        yield engine
    finally:
        await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Create an async session factory and yield a session"""
    async_session = async_sessionmaker(engine)  # Removed expire_on_commit=False
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

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
async def test_project_path():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        yield project_path

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