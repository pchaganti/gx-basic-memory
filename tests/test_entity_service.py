import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path
import tempfile
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from basic_memory.models import Base, Entity
from basic_memory.repository import EntityRepository
from basic_memory.services import EntityService, FileOperationError, DatabaseSyncError, EntityNotFoundError

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
        yield session

@pytest_asyncio.fixture
async def entity_repo(session):
    """Create an EntityRepository instance."""
    return EntityRepository(session, Entity)

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
    # Act
    entity = await entity_service.create_entity(
        name="Test Entity",
        type="test",
        description="test description"
    )
    
    # Assert Entity
    assert isinstance(entity, Entity)
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert entity.description == "test description"
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)
    
    # Verify file was created
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()
    content = entity_file.read_text()
    assert "Test Entity" in content

async def test_get_entity_success(entity_service):
    """Test successful entity retrieval."""
    # Arrange
    created = await entity_service.create_entity(
        name="Test Entity",
        type="test"
    )
    
    # Act
    retrieved = await entity_service.get_entity(created.id)
    
    # Assert
    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert retrieved.entity_type == created.entity_type

async def test_delete_entity_success(entity_service):
    """Test successful entity deletion."""
    # Arrange
    entity = await entity_service.create_entity(
        name="Test Entity",
        type="test"
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
    async def mock_db_fail(*args, **kwargs):
        raise DatabaseSyncError("Mock DB error")
    monkeypatch.setattr(entity_service, "_update_db_index", mock_db_fail)
    
    # Act
    entity = await entity_service.create_entity(
        name="Test Entity",
        type="test"
    )
    
    # Assert
    assert isinstance(entity, Entity)  # Should still return entity from file
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()  # File should still be created

async def test_delete_nonexistent_entity(entity_service):
    """Test deleting an entity that doesn't exist."""
    result = await entity_service.delete_entity("nonexistent-id")
    assert result is True  # Should succeed silently

# Edge Cases

async def test_create_entity_with_special_chars(entity_service):
    """Test entity creation with special characters in name."""
    name = "Test & Entity! With @ Special #Chars"
    entity = await entity_service.create_entity(name=name, type="test")
    
    assert entity.name == name
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()

async def test_create_entity_atomic_file_write(entity_service):
    """Test that file writing is atomic (uses temp file)."""
    # Act
    entity = await entity_service.create_entity(name="Test Entity", type="test")
    
    # Assert
    temp_file = entity_service.entities_path / f"{entity.id}.md.tmp"
    assert not temp_file.exists()  # Temp file should be cleaned up
    
    entity_file = entity_service.entities_path / f"{entity.id}.md"
    assert entity_file.exists()  # Final file should exist

async def test_rebuild_index(entity_service):
    """Test rebuilding database index from filesystem."""
    # Arrange - Create some entities
    entity1 = await entity_service.create_entity("Test 1", "test")
    entity2 = await entity_service.create_entity("Test 2", "test")
    
    # Act - Rebuild index
    await entity_service.rebuild_index()
    
    # Assert - Entities should be retrievable
    retrieved1 = await entity_service.get_entity(entity1.id)
    retrieved2 = await entity_service.get_entity(entity2.id)
    assert retrieved1.name == entity1.name
    assert retrieved2.name == entity2.name

# TODO: Add tests for:
# - Concurrent operations (using asyncio.gather)
# - Filesystem permissions issues
# - System crash simulation 
# - Markdown formatting edge cases
# - Very long entity names/content
# - Unicode/special character handling
# - File system space issues
