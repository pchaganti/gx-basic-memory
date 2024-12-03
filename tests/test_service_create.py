import pytest
from datetime import datetime
from pathlib import Path

from basic_memory.service import MemoryService, FileOperationError, DatabaseSyncError
from basic_memory.models import Entity

pytestmark = pytest.mark.asyncio


# Happy Path Tests

async def test_create_entity_success(memory_service):
    """Test successful entity creation."""
    # Act
    entity = await memory_service.create_entity(
        name="Test Entity",
        type="test",
        description="test description"
    )
    
    # Assert
    assert isinstance(entity, Entity)
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert entity.description == "test description"
    
    # Verify file was created
    entity_file = memory_service.project_path / "entities" / f"{entity.id}.md"
    assert entity_file.exists()
    content = entity_file.read_text()
    assert "Test Entity" in content

# Error Path Tests

async def test_create_entity_file_error(memory_service, monkeypatch):
    """Test handling of file write errors."""
    # Arrange - make file write fail
    async def mock_write_fail(*args, **kwargs):
        raise FileOperationError("Mock file write error")
    monkeypatch.setattr(memory_service, "_write_entity_file", mock_write_fail)
    
    # Act & Assert
    with pytest.raises(FileOperationError):
        await memory_service.create_entity(
            name="Test Entity",
            type="test"
        )

async def test_create_entity_db_error(memory_service, monkeypatch):
    """Test handling of database errors."""
    # Arrange - make db update fail but file write succeed
    async def mock_db_fail(*args, **kwargs):
        raise DatabaseSyncError("Mock DB error")
    monkeypatch.setattr(memory_service, "_update_db_index", mock_db_fail)
    
    # Act
    entity = await memory_service.create_entity(
        name="Test Entity",
        type="test"
    )
    
    # Assert
    assert isinstance(entity, Entity)  # Should still return entity from file
    entity_file = memory_service.project_path / "entities" / f"{entity.id}.md"
    assert entity_file.exists()  # File should still be created

# Edge Cases

async def test_create_entity_with_special_chars(memory_service):
    """Test entity creation with special characters in name."""
    name = "Test & Entity! With @ Special #Chars"
    entity = await memory_service.create_entity(name=name, type="test")
    
    assert entity.name == name
    entity_file = memory_service.project_path / "entities" / f"{entity.id}.md"
    assert entity_file.exists()

async def test_create_entity_atomic_file_write(memory_service):
    """Test that file writing is atomic (uses temp file)."""
    # Act
    entity = await memory_service.create_entity(name="Test Entity", type="test")
    
    # Assert
    temp_file = memory_service.project_path / "entities" / f"{entity.id}.md.tmp"
    assert not temp_file.exists()  # Temp file should be cleaned up
    
    entity_file = memory_service.project_path / "entities" / f"{entity.id}.md"
    assert entity_file.exists()  # Final file should exist

# TODO: Add tests for:
# - Concurrent operations
# - System crash simulation
# - Permission issues
# - File system full scenario
# - Long/unicode entity names
# - Empty/whitespace names
# - Other edge cases