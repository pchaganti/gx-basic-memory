import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path
import tempfile
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import delete

from basic_memory.models import Base, Entity as DbEntity, Observation as DbObservation
from basic_memory.repository import EntityRepository, ObservationRepository
from basic_memory.services import (
    EntityService, ObservationService,
    FileOperationError, DatabaseSyncError, ServiceError
)
from basic_memory.schemas import Entity, Observation
from basic_memory.fileio import read_entity_file

pytestmark = pytest.mark.asyncio

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
    async_session = async_sessionmaker(engine, expire_on_commit=False)
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
    return EntityRepository(session, DbEntity)

@pytest_asyncio.fixture
async def observation_repo(session):
    """Create an ObservationRepository instance."""
    return ObservationRepository(session, DbObservation)

@pytest_asyncio.fixture
async def entity_service(session, entity_repo):
    """Fixture providing initialized EntityService with temp directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        
        service = EntityService(project_path, entity_repo)
        yield service

@pytest_asyncio.fixture
async def observation_service(session, observation_repo):
    """Fixture providing initialized ObservationService."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        
        service = ObservationService(project_path, observation_repo)
        yield service

@pytest_asyncio.fixture
async def test_entity(entity_service):
    """Create a test entity for observation operations."""
    return await entity_service.create_entity(
        name="Test Entity",
        entity_type="test",
    )

# Happy Path Tests

async def test_add_observation_success(observation_service, test_entity):
    """Test successful observation addition."""
    # Act
    observation = await observation_service.add_observation(
        entity=test_entity,
        content="New observation",
        context="test-context"
    )
    
    # Assert
    assert isinstance(observation, Observation)
    assert observation.content == "New observation"
    
    # Verify file update
    entity = await read_entity_file(observation_service.entities_path, test_entity.id)
    assert len(entity.observations) == 1
    assert any(obs.content == "New observation" for obs in entity.observations)
    
    # Verify database index
    db_observations = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(db_observations) == 1
    assert any(obs.content == "New observation" and obs.context == "test-context"
              for obs in db_observations)

async def test_search_observations(observation_service, test_entity):
    """Test searching observations across entities."""
    # Arrange
    await observation_service.add_observation(test_entity, "Unique test content")
    await observation_service.add_observation(test_entity, "Other content")
    
    # Act
    results = await observation_service.search_observations("unique")
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "Unique test content"

async def test_get_observations_by_context(observation_service, test_entity):
    """Test retrieving observations by context."""
    # Arrange
    await observation_service.add_observation(
        test_entity,
        "Context observation",
        context="test-context"
    )
    await observation_service.add_observation(
        test_entity,
        "Other observation",
        context="other-context"
    )
    
    # Act
    results = await observation_service.get_observations_by_context("test-context")
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "Context observation"

# Error Path Tests

async def test_file_operation_error(observation_service, test_entity, monkeypatch):
    """Test handling of file operation errors."""
    async def mock_write(*args, **kwargs):
        raise FileOperationError("Mock file error")
    monkeypatch.setattr('basic_memory.services.write_entity_file', mock_write)
    
    with pytest.raises(FileOperationError):
        await observation_service.add_observation(
            test_entity,
            "Test observation"
        )

async def test_database_sync_error(observation_service, test_entity, monkeypatch):
    """Test handling of database sync errors."""
    async def mock_create(*args, **kwargs):
        raise Exception("Mock DB error")
    monkeypatch.setattr(observation_service.observation_repo, "create", mock_create)
    
    with pytest.raises(DatabaseSyncError):
        await observation_service.add_observation(
            test_entity,
            "Test observation"
        )

# Recovery Tests

async def test_rebuild_observation_index(observation_service, test_entity):
    """Test rebuilding observation index from filesystem."""
    # Arrange - Add observations and clear database
    await observation_service.add_observation(test_entity, "Test observation 1")
    await observation_service.add_observation(test_entity, "Test observation 2")
    
    # Clear database but keep files
    await observation_service.observation_repo.execute_query(delete(DbObservation))
    
    # Act
    await observation_service.rebuild_observation_index()
    
    # Assert
    db_observations = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(db_observations) == 2
    observation_contents = {obs.content for obs in db_observations}
    assert observation_contents == {
        "Test observation 1",
        "Test observation 2"
    }

# Edge Cases

async def test_observation_with_special_characters(observation_service, test_entity):
    """Test handling observations with special characters."""
    content = "Test & observation with @#$% special chars!"
    observation = await observation_service.add_observation(
        test_entity,
        content
    )
    assert observation.content == content
    
    # Verify file content
    entity = await read_entity_file(observation_service.entities_path, test_entity.id)
    assert any(obs.content == content for obs in entity.observations)


async def test_very_long_observation(observation_service, test_entity):
    """Test handling very long observation content."""
    long_content = "Very long observation " * 100  # ~1800 characters
    observation = await observation_service.add_observation(
        test_entity,
        long_content
    )
    assert observation.content == long_content

    # Debug print actual file content
    entity_path = observation_service.entities_path / f"{test_entity.id}.md"
    print("File content:", entity_path.read_text())

    # Verify file content
    entity = await read_entity_file(observation_service.entities_path, test_entity.id)
    print("Loaded observations:", [obs.content for obs in entity.observations])
    assert observation.content.rstrip() == entity.observations[0].content.rstrip()


# TODO: Add concurrent operation tests once we have proper session management
# Currently SQLAlchemy sessions are not safe for concurrent use.
# We'll need either:
# 1. Session per operation pattern
# 2. Higher level concurrency handling (e.g., API layer)
# See error: IllegalStateChangeError with concurrent session usage