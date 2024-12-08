"""Tests for EntityService."""
import pytest

from basic_memory.fileio import EntityNotFoundError
from basic_memory.models import Entity
from basic_memory.schemas import EntityIn

pytestmark = pytest.mark.asyncio


async def test_create_entity_success(entity_service):
    """Test successful entity creation."""
    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
    )
    
    # Act
    entity = await entity_service.create_entity(entity_data)
    
    # Assert Entity
    assert isinstance(entity, Entity)
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert entity.created_at is not None

async def test_get_entity_success(entity_service):
    """Test successful entity retrieval."""
    # Arrange
    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
    )
    created = await entity_service.create_entity(entity_data)
    
    # Act
    retrieved = await entity_service.get_entity(created.id)
    
    # Assert
    assert isinstance(retrieved, Entity)
    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert retrieved.entity_type == created.entity_type
    # relations are tested in test_memory_service

async def test_delete_entity_success(entity_service):
    """Test successful entity deletion."""
    # Arrange
    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
    )
    entity = await entity_service.create_entity(entity_data)

    # Act
    result = await entity_service.delete_entity(entity.id)
    
    # Assert
    assert result is True
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

    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
    )

    # Act/Assert
    with pytest.raises(Exception, match="Mock DB error"):
        await entity_service.create_entity(entity_data)

async def test_delete_nonexistent_entity(entity_service):
    """Test deleting an entity that doesn't exist."""
    await entity_service.delete_entity("nonexistent-id")
    # If we get here, the deletion succeeded or failed silently as expected

# Edge Cases

async def test_create_entity_with_special_chars(entity_service):
    """Test entity creation with special characters in name."""
    name = "Test & Entity! With @ Special #Chars"
    entity_data = EntityIn(
        name=name,
        entity_type="test",
    )
    entity = await entity_service.create_entity(entity_data)
    
    assert entity.name == name


async def test_entity_id_generation(entity_service):
    """Test that entities get unique IDs generated correctly."""
    entity_data = EntityIn(
        name="Test Entity",
        entity_type="test",
        observations=[]
    )
    
    entity = await entity_service.create_entity(entity_data)
    
    assert entity.id  # ID should be generated
    assert "-test-entity" in entity.id  # Should contain normalized name
