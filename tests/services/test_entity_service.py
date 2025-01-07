"""Tests for EntityService."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory.models import Entity as EntityModel
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import Entity as EntitySchema, EntityType
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
    entity_data = EntitySchema(
        name="TestEntity",
        entity_type=EntityType.KNOWLEDGE,
        description="A test entity description",
        observations=["this is a test observation"],
    )

    # Act
    entity = await entity_service.create_entity(entity_data)

    # Assert Entity
    assert isinstance(entity, EntityModel)
    assert entity.name == "TestEntity"
    assert entity.path_id == entity_data.path_id
    assert entity.file_path == entity_data.file_path
    assert entity.entity_type == EntityType.KNOWLEDGE
    assert entity.description == "A test entity description"
    assert entity.created_at is not None
    assert entity.observations[0].content == "this is a test observation"
    assert len(entity.relations) == 0

    # Verify we can retrieve it using path_id
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)
    assert retrieved.description == "A test entity description"
    assert retrieved.name == "TestEntity"
    assert retrieved.entity_type == EntityType.KNOWLEDGE
    assert retrieved.description == "A test entity description"
    assert retrieved.created_at is not None
    assert retrieved.observations[0].content == "this is a test observation"


async def test_create_entities(entity_service: EntityService):
    """Test successful entity creation."""
    entity_data = [
        EntitySchema(
            name="TestEntity1",
            entity_type=EntityType.KNOWLEDGE,
            description="A test entity description",
            observations=["this is a test observation"],
        ),
        EntitySchema(
            name="TestEntity2",
            entity_type=EntityType.KNOWLEDGE,
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
    assert entity1.name == "TestEntity1"
    assert entity1.entity_type == EntityType.KNOWLEDGE
    assert entity1.description == "A test entity description"
    assert entity1.created_at is not None
    assert entity1.observations[0].content == "this is a test observation"
    assert len(entity1.relations) == 0

    entity2 = entities[1]
    assert isinstance(entity1, EntityModel)
    assert entity2.name == "TestEntity2"
    assert entity2.entity_type == EntityType.KNOWLEDGE
    assert entity2.description == "A test entity description"
    assert entity2.created_at is not None
    assert entity2.observations[0].content == "this is a test observation"

    # Verify we can retrieve them using path_ids
    retrieved1 = await entity_service.get_by_path_id(entity_data[0].path_id)
    assert retrieved1.description == "A test entity description"

    retrieved2 = await entity_service.get_by_path_id(entity_data[1].path_id)
    assert retrieved2.description == "A test entity description"


async def test_get_by_path_id(entity_service: EntityService):
    """Test finding entity by type and name combination."""
    entity1_data = EntitySchema(
        name="TestEntity1",
        entity_type=EntityType.KNOWLEDGE,
        description="First test entity",
        observations=[],
    )
    entity1 = await entity_service.create_entity(entity1_data)

    entity2_data = EntitySchema(
        name="TestEntity2", 
        entity_type=EntityType.KNOWLEDGE,
        description="Second test entity",
        observations=[],
    )
    entity2 = await entity_service.create_entity(entity2_data)

    # Find by type1 and name
    found = await entity_service.get_by_path_id(entity1_data.path_id)
    assert found is not None
    assert found.id == entity1.id
    assert found.entity_type == entity1.entity_type
    assert found.description == "First test entity"

    # Find by type2 and name
    found = await entity_service.get_by_path_id(entity2_data.path_id)
    assert found is not None
    assert found.id == entity2.id
    assert found.entity_type == entity2.entity_type
    assert found.description == "Second test entity"

    # Test not found case
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_path_id("nonexistent/test_entity")


async def test_create_entity_no_description(entity_service: EntityService):
    """Test creating entity without description (should be None)."""
    entity_data = EntitySchema(name="TestEntity", entity_type=EntityType.KNOWLEDGE, observations=[])

    entity = await entity_service.create_entity(entity_data)
    assert entity.description is None

    # Verify after retrieval
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)
    assert retrieved.description is None


async def test_get_entity_success(entity_service: EntityService):
    """Test successful entity retrieval."""
    entity_data = EntitySchema(
        name="TestEntity",
        entity_type=EntityType.KNOWLEDGE,
        description="Test description",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Get by path ID
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)

    assert isinstance(retrieved, EntityModel)
    assert retrieved.name == "TestEntity"
    assert retrieved.entity_type == EntityType.KNOWLEDGE
    assert retrieved.description == "Test description"


async def test_update_entity_description(entity_service: EntityService):
    """Test updating an entity's description."""
    entity_data = EntitySchema(
        name="TestEntity",
        entity_type=EntityType.KNOWLEDGE,
        description="Initial description",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Update description using path_id
    updated = await entity_service.update_entity(
        entity_data.path_id, {"description": "Updated description"}
    )
    assert updated.description == "Updated description"

    # Verify after retrieval
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)
    assert retrieved.description == "Updated description"


async def test_update_entity_description_to_none(entity_service: EntityService):
    """Test updating an entity's description to None."""
    entity_data = EntitySchema(
        name="TestEntity",
        entity_type=EntityType.KNOWLEDGE,
        description="Initial description",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Update description to None using path_id
    updated = await entity_service.update_entity(entity_data.path_id, {"description": None})
    assert updated.description is None

    # Verify after retrieval
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)
    assert retrieved.description is None


async def test_delete_entity_success(entity_service: EntityService):
    """Test successful entity deletion."""
    entity_data = EntitySchema(
        name="TestEntity",
        entity_type=EntityType.KNOWLEDGE,
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Act using path_id
    result = await entity_service.delete_entity(entity_data.path_id)

    # Assert
    assert result is True
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_path_id(entity_data.path_id)


async def test_get_entity_by_path_id_not_found(entity_service: EntityService):
    """Test handling of non-existent entity retrieval."""
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_path_id("test/non_existent")


async def test_delete_nonexistent_entity(entity_service: EntityService):
    """Test deleting an entity that doesn't exist."""
    with pytest.raises(EntityNotFoundError):
        await entity_service.delete_entity("test/non_existent")


async def test_create_entity_with_special_chars(entity_service: EntityService):
    """Test entity creation with special characters in name and description."""
    name = "TestEntity_Special"  # Note: Using valid path characters
    description = "Description with $pecial chars & symbols!"
    entity_data = EntitySchema(
        name=name,
        entity_type=EntityType.KNOWLEDGE,
        description=description,
    )
    entity = await entity_service.create_entity(entity_data)

    assert entity.name == name
    assert entity.description == description

    # Verify after retrieval using path_id
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)
    assert retrieved.description == description


async def test_create_entity_long_description(entity_service: EntityService):
    """Test creating entity with a long description."""
    long_description = "A" * 1000  # 1000 character description
    entity_data = EntitySchema(
        name="TestEntity",
        entity_type=EntityType.KNOWLEDGE,
        description=long_description,
        observations=[],
    )

    entity = await entity_service.create_entity(entity_data)
    assert entity.description == long_description

    # Verify after retrieval using path_id
    retrieved = await entity_service.get_by_path_id(entity_data.path_id)
    assert retrieved.description == long_description


async def test_open_nodes_by_path_ids(entity_service: EntityService):
    """Test opening multiple nodes by path IDs."""
    # Create test entities
    entity1_data = EntitySchema(
        name="Entity1",
        entity_type=EntityType.KNOWLEDGE,
        description="First entity",
        observations=[],
    )
    entity2_data = EntitySchema(
        name="Entity2",
        entity_type=EntityType.KNOWLEDGE,
        description="Second entity",
        observations=[],
    )
    await entity_service.create_entity(entity1_data)
    await entity_service.create_entity(entity2_data)

    # Open nodes by path IDs
    path_ids = [entity1_data.path_id, entity2_data.path_id]
    found = await entity_service.open_nodes(path_ids)

    assert len(found) == 2
    names = {e.name for e in found}
    assert names == {"Entity1", "Entity2"}


async def test_open_nodes_empty_input(entity_service: EntityService):
    """Test opening nodes with empty path ID list."""
    found = await entity_service.open_nodes([])
    assert len(found) == 0


async def test_open_nodes_some_not_found(entity_service: EntityService):
    """Test opening nodes with mix of existing and non-existent path IDs."""
    # Create one test entity
    entity_data = EntitySchema(
        name="Entity1",
        entity_type=EntityType.KNOWLEDGE,
        description="Test entity",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Try to open two nodes, one exists, one doesn't
    path_ids = [entity_data.path_id, "type1/non_existent"]
    found = await entity_service.open_nodes(path_ids)

    assert len(found) == 1
    assert found[0].name == "Entity1"


async def test_delete_entities_by_path_ids(entity_service: EntityService):
    """Test deleting multiple entities by path IDs."""
    # Create test entities
    entity1_data = EntitySchema(
        name="Entity1",
        entity_type=EntityType.KNOWLEDGE,
        description="First entity",
        observations=[],
    )
    entity2_data = EntitySchema(
        name="Entity2",
        entity_type=EntityType.KNOWLEDGE,
        description="Second entity",
        observations=[],
    )
    await entity_service.create_entity(entity1_data)
    await entity_service.create_entity(entity2_data)

    # Delete by path IDs
    path_ids = [entity1_data.path_id, entity2_data.path_id]
    result = await entity_service.delete_entities(path_ids)
    assert result is True

    # Verify both are deleted
    for path_id in path_ids:
        with pytest.raises(EntityNotFoundError):
            await entity_service.get_by_path_id(path_id)


async def test_delete_entities_empty_input(entity_service: EntityService):
    """Test deleting entities with empty path ID list."""
    result = await entity_service.delete_entities([])
    assert result is False


async def test_delete_entities_none_found(entity_service: EntityService):
    """Test deleting non-existent entities by path IDs."""
    path_ids = ["type1/NonExistent1", "type2/NonExistent2"]
    result = await entity_service.delete_entities(path_ids)
    assert result is False
