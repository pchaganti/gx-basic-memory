import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path
import tempfile
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from basic_memory.fileio import EntityNotFoundError
from basic_memory.models import Entity as DbEntity, Base
from basic_memory.repository import EntityRepository
from basic_memory.services import EntityService, ServiceError, DatabaseSyncError
from basic_memory.schemas import Entity, Observation

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create an async engine using in-memory SQLite database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",  # In-memory database
        echo=False,  # Set to True for SQL logging
        poolclass=StaticPool,  # Ensure single connection for in-memory db
        connect_args={"check_same_thread": False}  # Allow multi-threaded access
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
async def entity_service(session, entity_repo):
    """Fixture providing initialized EntityService with temp directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        
        service = EntityService(project_path, entity_repo)
        yield service

# Happy Path Tests

async def test_create_entity_success(entity_service):
    """Test successful entity creation."""
    observations = ["First observation", "Second observation"]
    
    # Act
    entity = await entity_service.create_entity(
        name="Test Entity",
        entity_type="test",
        observations=observations
    )
    
    # Assert Entity
    assert isinstance(entity, Entity)
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert len(entity.observations) == 2
    assert entity.observations[0].content == "First observation"
    assert entity.observations[1].content == "Second observation"
    
    # Verify file was created
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()
    content = entity_file.read_text()
    assert "# Test Entity" in content
    assert "type: test" in content
    assert "First observation" in content
    assert "Second observation" in content

async def test_get_entity_success(entity_service):
    """Test successful entity retrieval."""
    # Arrange
    observations = ["Test observation"]
    created = await entity_service.create_entity(
        name="Test Entity",
        entity_type="test",
        observations=observations
    )
    
    # Act
    retrieved = await entity_service.get_entity(created.id)
    
    # Assert
    assert isinstance(retrieved, Entity)
    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert retrieved.entity_type == created.entity_type
    assert len(retrieved.observations) == 1
    assert retrieved.observations[0].content == "Test observation"

async def test_delete_entity_success(entity_service):
    """Test successful entity deletion."""
    # Arrange
    entity = await entity_service.create_entity(
        name="Test Entity",
        entity_type="test",
        observations=["Test observation"]
    )
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()
    
    # Act
    result = await entity_service.delete_entity(entity.id)
    
    # Assert
    assert result is True
    assert not entity_file.exists()
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_entity(entity.id)

# Error Path Tests

async def test_get_entity_not_found(entity_service):
    """Test handling of non-existent entity retrieval."""
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_entity("nonexistent-id")

async def test_create_entity_db_error(entity_service, monkeypatch):
    """Test handling of database errors during creation."""
    # Arrange - make db operations fail
    async def mock_create(*args, **kwargs):
        raise Exception("Mock DB error")
    monkeypatch.setattr(entity_service.entity_repo, "create", mock_create)

    # Act/Assert - both file and DB operations should fail
    with pytest.raises(Exception, match="Mock DB error"):
        await entity_service.create_entity(
            name="Test Entity",
            entity_type="test",
            observations=["Test observation"]
        )

async def test_delete_nonexistent_entity(entity_service):
    """Test deleting an entity that doesn't exist."""
    await entity_service.delete_entity("nonexistent-id")
    # If we get here, the deletion succeeded or failed silently as expected

# Edge Cases

async def test_create_entity_with_special_chars(entity_service):
    """Test entity creation with special characters in name."""
    name = "Test & Entity! With @ Special #Chars"
    entity = await entity_service.create_entity(
        name=name, 
        entity_type="test",
        observations=["Test observation"]
    )
    
    assert entity.name == name
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()

async def test_create_entity_atomic_file_write(entity_service):
    """Test that file writing is atomic (uses temp file)."""
    # Act
    entity = await entity_service.create_entity(
        name="Test Entity", 
        entity_type="test",
        observations=["Test observation"]
    )
    
    # Assert
    temp_file = entity_service.entities_path / f"{entity.id}.md.tmp"
    assert not temp_file.exists()  # Temp file should be cleaned up
    
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()  # Final file should exist

async def test_rebuild_index(entity_service):
    """Test rebuilding database index from filesystem."""
    # Arrange - Create some entities
    entity1 = await entity_service.create_entity(
        name="Test 1", 
        entity_type="test",
        observations=["Test observation 1"]
    )
    entity2 = await entity_service.create_entity(
        name="Test 2", 
        entity_type="test",
        observations=["Test observation 2"]
    )
    
    # Act - Rebuild index
    await entity_service.rebuild_index()
    
    # Assert - Entities should be retrievable
    retrieved1 = await entity_service.get_entity(entity1.id)
    retrieved2 = await entity_service.get_entity(entity2.id)
    
    assert isinstance(retrieved1, Entity)
    assert isinstance(retrieved2, Entity)
    assert retrieved1.name == entity1.name
    assert retrieved2.name == entity2.name
    assert retrieved1.observations[0].content == "Test observation 1"
    assert retrieved2.observations[0].content == "Test observation 2"

# Tests for Pydantic Model Behavior

async def test_entity_id_generation(entity_service):
    """Test that entities get unique IDs generated correctly."""
    entity = await entity_service.create_entity(
        name="Test Entity",
        entity_type="test"
    )
    
    assert entity.id  # ID should be generated
    assert "-test-entity-" in entity.id  # Should contain normalized name
    assert len(entity.id.split("-")[-1]) == 8  # UUID part should be 8 chars

async def test_entity_with_no_observations(entity_service):
    """Test entity creation with no observations."""
    entity = await entity_service.create_entity(
        name="Test Entity",
        entity_type="test"
    )
    
    assert isinstance(entity, Entity)
    assert entity.observations == []
    
    # Check file format
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    content = entity_file.read_text()
    assert "## Observations" in content
    assert content.strip().endswith("## Observations")  # No observations after header

# TODO: Add tests for:
# - Concurrent operations (using asyncio.gather)
# - Filesystem permissions issues
# - System crash simulation 
# - Markdown formatting edge cases
# - Very long entity names/content
# - Unicode/special character handling
# - File system space issues