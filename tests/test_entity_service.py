"""Tests for EntityService."""
import pytest

from basic_memory.fileio import EntityNotFoundError
from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity

pytestmark = pytest.mark.asyncio


async def test_create_entity_success(entity_service):
    """Test successful entity creation."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="A test entity description"
    )
    
    # Act
    entity = await entity_service.create_entity(entity_data)
    
    # Assert Entity
    assert isinstance(entity, EntityModel)
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert entity.description == "A test entity description"
    assert entity.created_at is not None

    # Verify we can retrieve it
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == "A test entity description"

async def test_get_by_type_and_name(entity_service):
    """Test finding entity by type and name combination."""
    # Create two entities with same name but different types
    entity1_data = Entity(
        name="Test Entity",
        entity_type="type1",
        description="First test entity"
    )
    entity1 = await entity_service.create_entity(entity1_data)

    entity2_data = Entity(
        name="Test Entity",  # Same name
        entity_type="type2",  # Different type
        description="Second test entity"
    )
    entity2 = await entity_service.create_entity(entity2_data)

    # Find by type1 and name
    found = await entity_service.get_by_type_and_name("type1", "Test Entity")
    assert found is not None
    assert found.id == entity1.id
    assert found.entity_type == "type1"
    assert found.description == "First test entity"

    # Find by type2 and name
    found = await entity_service.get_by_type_and_name("type2", "Test Entity")
    assert found is not None
    assert found.id == entity2.id
    assert found.entity_type == "type2"
    assert found.description == "Second test entity"

    # Test not found case
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_type_and_name("nonexistent", "Test Entity")

async def test_create_entity_no_description(entity_service):
    """Test creating entity without description (should be None)."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
    )
    
    entity = await entity_service.create_entity(entity_data)
    assert entity.description is None

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description is None

async def test_get_entity_success(entity_service):
    """Test successful entity retrieval."""
    # Arrange
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Test description"
    )
    created = await entity_service.create_entity(entity_data)
    
    # Act
    retrieved = await entity_service.get_entity(created.id)
    
    # Assert
    assert isinstance(retrieved, EntityModel)
    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert retrieved.entity_type == created.entity_type
    assert retrieved.description == "Test description"
    # relations are tested in test_memory_service

async def test_update_entity_description(entity_service):
    """Test updating an entity's description."""
    # Create entity with description
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Initial description"
    )
    entity = await entity_service.create_entity(entity_data)
    
    # Update description
    updated = await entity_service.update_entity(entity.id, {"description": "Updated description"})
    assert updated.description == "Updated description"

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == "Updated description"

async def test_update_entity_description_to_none(entity_service):
    """Test updating an entity's description to None."""
    # Create entity with description
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Initial description"
    )
    entity = await entity_service.create_entity(entity_data)
    
    # Update description to None
    updated = await entity_service.update_entity(entity.id, {"description": None})
    assert updated.description is None

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description is None

async def test_delete_entity_success(entity_service):
    """Test successful entity deletion."""
    # Arrange
    entity_data = Entity(
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

    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Test description"
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
    """Test entity creation with special characters in name and description."""
    name = "Test & Entity! With @ Special #Chars"
    description = "Description with $pecial chars & symbols!"
    entity_data = Entity(
        name=name,
        entity_type="test",
        description=description
    )
    entity = await entity_service.create_entity(entity_data)
    
    assert entity.name == name
    assert entity.description == description

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == description

async def test_entity_id_generation(entity_service):
    """Test that entities get unique IDs generated correctly."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Test description",
        observations=[]
    )
    
    entity = await entity_service.create_entity(entity_data)
    
    assert entity.id  # ID should be generated
    assert "test/test_entity" ==  entity.id  # Should contain normalized name

async def test_create_entity_long_description(entity_service):
    """Test creating entity with a long description."""
    long_description = "A" * 1000  # 1000 character description
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description=long_description
    )
    
    entity = await entity_service.create_entity(entity_data)
    assert entity.description == long_description

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == long_description