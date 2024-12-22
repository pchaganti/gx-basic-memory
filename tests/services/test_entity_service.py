"""Tests for EntityService."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory.models import Entity as EntityModel
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import Entity
from basic_memory.services.entity_service import EntityService
from basic_memory.services.exceptions import EntityNotFoundError

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def entity_repository(session_maker: async_sessionmaker[AsyncSession]) -> EntityRepository:
    """Create an EntityRepository instance."""
    return EntityRepository(session_maker)


@pytest_asyncio.fixture
async def entity_service(entity_repository: EntityRepository) -> EntityService:
    """Create EntityService with repository."""
    return EntityService(entity_repository)


async def test_create_entity(entity_service: EntityService):
    """Test successful entity creation."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="A test entity description",
        observations=["this is a test observation"],
    )

    # Act
    entity = await entity_service.create_entity(entity_data)

    # Assert Entity
    assert isinstance(entity, EntityModel)
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert entity.description == "A test entity description"
    assert entity.created_at is not None
    assert entity.observations[0].content == "this is a test observation"
    assert len(entity.relations) == 0

    # Verify we can retrieve it
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == "A test entity description"
    assert retrieved.name == "Test Entity"
    assert retrieved.entity_type == "test"
    assert retrieved.description == "A test entity description"
    assert retrieved.created_at is not None
    assert retrieved.observations[0].content == "this is a test observation"


async def test_create_entities(entity_service: EntityService):
    """Test successful entity creation."""
    entity_data = [
        Entity(
            name="Test Entity_1",
            entity_type="test",
            description="A test entity description",
            observations=["this is a test observation"],
        ),
        Entity(
            name="Test Entity_2",
            entity_type="test",
            description="A test entity description",
            observations=["this is a test observation"],
        ),
    ]

    # Act
    entities = await entity_service.create_entities(entity_data)

    # Assert Entity
    assert len(entities) == 2
    entity1 = entities[0]
    assert isinstance(entity1, EntityModel)
    assert entity1.name == "Test Entity_1"
    assert entity1.entity_type == "test"
    assert entity1.description == "A test entity description"
    assert entity1.created_at is not None
    assert entity1.observations[0].content == "this is a test observation"
    assert len(entity1.relations) == 0

    entity2 = entities[1]
    assert isinstance(entity1, EntityModel)
    assert entity2.name == "Test Entity_2"
    assert entity2.entity_type == "test"
    assert entity2.description == "A test entity description"
    assert entity2.created_at is not None
    assert entity2.observations[0].content == "this is a test observation"

    # Verify we can retrieve them
    retrieved1 = await entity_service.get_entity(entity1.id)
    assert retrieved1.description == "A test entity description"

    retrieved2 = await entity_service.get_entity(entity2.id)
    assert retrieved2.description == "A test entity description"


async def test_get_by_type_and_name(entity_service: EntityService):
    """Test finding entity by type and name combination."""
    # Create two entities with same name but different types
    entity1_data = Entity(
        name="Test Entity",
        entity_type="type1",
        description="First test entity",
        observations=[],
    )
    entity1 = await entity_service.create_entity(entity1_data)

    entity2_data = Entity(
        name="Test Entity",  # Same name
        entity_type="type2",  # Different type
        description="Second test entity",
        observations=[],
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


async def test_create_entity_no_description(entity_service: EntityService):
    """Test creating entity without description (should be None)."""
    entity_data = Entity(name="Test Entity", entity_type="test", observations=[], relations=[])

    entity = await entity_service.create_entity(entity_data)
    assert entity.description is None

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description is None


async def test_get_entity_success(entity_service: EntityService):
    """Test successful entity retrieval."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Test description",
        observations=[],
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


async def test_update_entity_description(entity_service: EntityService):
    """Test updating an entity's description."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Initial description",
        observations=[],
    )
    entity = await entity_service.create_entity(entity_data)

    # Update description
    updated = await entity_service.update_entity(entity.id, {"description": "Updated description"})
    assert updated.description == "Updated description"

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == "Updated description"


async def test_update_entity_description_to_none(entity_service: EntityService):
    """Test updating an entity's description to None."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Initial description",
        observations=[],
    )
    entity = await entity_service.create_entity(entity_data)

    # Update description to None
    updated = await entity_service.update_entity(entity.id, {"description": None})
    assert updated.description is None

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description is None


async def test_delete_entity_success(entity_service: EntityService):
    """Test successful entity deletion."""
    entity_data = Entity(name="Test Entity", entity_type="test", observations=[], relations=[])
    entity = await entity_service.create_entity(entity_data)

    # Act
    result = await entity_service.delete_entity(entity.id)

    # Assert
    assert result is True
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_entity(entity.id)


async def test_get_entity_not_found(entity_service: EntityService):
    """Test handling of non-existent entity retrieval."""
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_entity("nonexistent-id")


async def test_delete_nonexistent_entity(entity_service: EntityService):
    """Test deleting an entity that doesn't exist."""
    result = await entity_service.delete_entity("nonexistent-id")
    assert result is False


async def test_create_entity_with_special_chars(entity_service: EntityService):
    """Test entity creation with special characters in name and description."""
    name = "Test & Entity! With @ Special #Chars"
    description = "Description with $pecial chars & symbols!"
    entity_data = Entity(
        name=name, entity_type="test", description=description, observations=[], relations=[]
    )
    entity = await entity_service.create_entity(entity_data)

    assert entity.name == name
    assert entity.description == description

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == description


async def test_entity_id_generation(entity_service: EntityService):
    """Test that entities get unique IDs generated correctly."""
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description="Test description",
        observations=[],
    )

    entity = await entity_service.create_entity(entity_data)

    assert entity.id  # ID should be generated
    assert "test/test_entity" == entity.id  # Should contain normalized name


async def test_create_entity_long_description(entity_service: EntityService):
    """Test creating entity with a long description."""
    long_description = "A" * 1000  # 1000 character description
    entity_data = Entity(
        name="Test Entity",
        entity_type="test",
        description=long_description,
        observations=[],
    )

    entity = await entity_service.create_entity(entity_data)
    assert entity.description == long_description

    # Verify after retrieval
    retrieved = await entity_service.get_entity(entity.id)
    assert retrieved.description == long_description
