"""Tests for EntityService."""

from pathlib import Path

import pytest
import yaml

from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.services import FileService
from basic_memory.services.entity_service import EntityService
from basic_memory.services.exceptions import EntityNotFoundError

pytestmark = pytest.mark.asyncio


async def test_create_entity(entity_service: EntityService, file_service: FileService):
    """Test successful entity creation."""
    entity_data = EntitySchema(
        title="TestEntity",
        entity_type="test",
        summary="A test entity description",
        observations=["this is a test observation"],
    )

    # Act
    entity = await entity_service.create_entity(entity_data)

    # Assert Entity
    assert isinstance(entity, EntityModel)
    assert entity.title == "TestEntity"
    assert entity.permalink == entity_data.permalink
    assert entity.file_path == entity_data.file_path
    assert entity.entity_type == "test"
    assert entity.summary == "A test entity description"
    assert entity.created_at is not None
    assert entity.observations[0].content == "this is a test observation"
    assert len(entity.relations) == 0

    # Verify we can retrieve it using permalink
    retrieved = await entity_service.get_by_permalink(entity_data.permalink)
    assert retrieved.summary == "A test entity description"
    assert retrieved.title == "TestEntity"
    assert retrieved.entity_type == "test"
    assert retrieved.summary == "A test entity description"
    assert retrieved.created_at is not None
    assert retrieved.observations[0].content == "this is a test observation"

    # Verify file was written
    file_path = file_service.get_entity_path(entity)
    assert await file_service.exists(file_path)

    file_content, _ = await file_service.read_file(file_path)
    _, frontmatter, doc_content = file_content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)

    # Verify frontmatter contents
    assert metadata["id"] == entity.permalink
    assert metadata["type"] == entity.entity_type
    assert "created" in metadata
    assert "modified" in metadata


async def test_create_entities(entity_service: EntityService, file_service: FileService):
    """Test successful entity creation."""
    entity_data = [
        EntitySchema(
            title="TestEntity1",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
        EntitySchema(
            title="TestEntity2",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
    ]

    # Act
    entities = await entity_service.create_entities(entity_data)

    # Assert Entity
    assert len(entities) == 2
    entity1 = entities[0]
    assert isinstance(entity1, EntityModel)
    assert entity1.title == "TestEntity1"
    assert entity1.entity_type == "test"
    assert entity1.summary == "A test entity description"
    assert entity1.created_at is not None
    assert entity1.observations[0].content == "this is a test observation"
    assert len(entity1.relations) == 0

    entity2 = entities[1]
    assert isinstance(entity1, EntityModel)
    assert entity2.title == "TestEntity2"
    assert entity2.entity_type == "test"
    assert entity2.summary == "A test entity description"
    assert entity2.created_at is not None
    assert entity2.observations[0].content == "this is a test observation"

    # Verify we can retrieve them using permalinks
    retrieved1 = await entity_service.get_by_permalink(entity_data[0].permalink)
    assert retrieved1.summary == "A test entity description"

    retrieved2 = await entity_service.get_by_permalink(entity_data[1].permalink)
    assert retrieved2.summary == "A test entity description"

    # verify files are written
    for i, entity in enumerate(entities):
        file_path = file_service.get_entity_path(entity)
        assert await file_service.exists(file_path)


async def test_get_by_permalink(entity_service: EntityService):
    """Test finding entity by type and name combination."""
    entity1_data = EntitySchema(
        title="TestEntity1",
        entity_type="test",
        summary="First test entity",
        observations=[],
    )
    entity1 = await entity_service.create_entity(entity1_data)

    entity2_data = EntitySchema(
        title="TestEntity2",
        entity_type="test",
        summary="Second test entity",
        observations=[],
    )
    entity2 = await entity_service.create_entity(entity2_data)

    # Find by type1 and name
    found = await entity_service.get_by_permalink(entity1_data.permalink)
    assert found is not None
    assert found.id == entity1.id
    assert found.entity_type == entity1.entity_type
    assert found.summary == "First test entity"

    # Find by type2 and name
    found = await entity_service.get_by_permalink(entity2_data.permalink)
    assert found is not None
    assert found.id == entity2.id
    assert found.entity_type == entity2.entity_type
    assert found.summary == "Second test entity"

    # Test not found case
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_permalink("nonexistent/test_entity")


async def test_create_entity_no_description(entity_service: EntityService):
    """Test creating entity without description (should be None)."""
    entity_data = EntitySchema(title="TestEntity", entity_type="test", observations=[])

    entity = await entity_service.create_entity(entity_data)
    assert entity.summary is None

    # Verify after retrieval
    retrieved = await entity_service.get_by_permalink(entity_data.permalink)
    assert retrieved.summary is None


async def test_get_entity_success(entity_service: EntityService):
    """Test successful entity retrieval."""
    entity_data = EntitySchema(
        title="TestEntity",
        entity_type="test",
        summary="Test description",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Get by path ID
    retrieved = await entity_service.get_by_permalink(entity_data.permalink)

    assert isinstance(retrieved, EntityModel)
    assert retrieved.title == "TestEntity"
    assert retrieved.entity_type == "test"
    assert retrieved.summary == "Test description"


async def test_delete_entity_success(entity_service: EntityService):
    """Test successful entity deletion."""
    entity_data = EntitySchema(
        title="TestEntity",
        entity_type="test",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Act using permalink
    result = await entity_service.delete_entity(entity_data.permalink)

    # Assert
    assert result is True
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_permalink(entity_data.permalink)


async def test_get_entity_by_permalink_not_found(entity_service: EntityService):
    """Test handling of non-existent entity retrieval."""
    with pytest.raises(EntityNotFoundError):
        await entity_service.get_by_permalink("test/non_existent")


async def test_delete_nonexistent_entity(entity_service: EntityService):
    """Test deleting an entity that doesn't exist."""
    assert await entity_service.delete_entity("test/non_existent") is True


async def test_create_entity_with_special_chars(entity_service: EntityService):
    """Test entity creation with special characters in name and description."""
    name = "TestEntity_Special"  # Note: Using valid path characters
    description = "Description with $pecial chars & symbols!"
    entity_data = EntitySchema(
        title=name,
        entity_type="test",
        summary=description,
    )
    entity = await entity_service.create_entity(entity_data)

    assert entity.title == name
    assert entity.summary == description

    # Verify after retrieval using permalink
    retrieved = await entity_service.get_by_permalink(entity_data.permalink)
    assert retrieved.summary == description


async def test_create_entity_long_description(entity_service: EntityService):
    """Test creating entity with a long description."""
    long_description = "A" * 1000  # 1000 character description
    entity_data = EntitySchema(
        title="TestEntity",
        entity_type="test",
        summary=long_description,
        observations=[],
    )

    entity = await entity_service.create_entity(entity_data)
    assert entity.summary == long_description

    # Verify after retrieval using permalink
    retrieved = await entity_service.get_by_permalink(entity_data.permalink)
    assert retrieved.summary == long_description


async def test_open_nodes_by_permalinks(entity_service: EntityService):
    """Test opening multiple nodes by path IDs."""
    # Create test entities
    entity1_data = EntitySchema(
        title="Entity1",
        entity_type="test",
        summary="First entity",
        observations=[],
    )
    entity2_data = EntitySchema(
        title="Entity2",
        entity_type="test",
        summary="Second entity",
        observations=[],
    )
    await entity_service.create_entity(entity1_data)
    await entity_service.create_entity(entity2_data)

    # Open nodes by path IDs
    permalinks = [entity1_data.permalink, entity2_data.permalink]
    found = await entity_service.get_entities_by_permalinks(permalinks)

    assert len(found) == 2
    names = {e.title for e in found}
    assert names == {"Entity1", "Entity2"}


async def test_open_nodes_empty_input(entity_service: EntityService):
    """Test opening nodes with empty path ID list."""
    found = await entity_service.get_entities_by_permalinks([])
    assert len(found) == 0


async def test_open_nodes_some_not_found(entity_service: EntityService):
    """Test opening nodes with mix of existing and non-existent path IDs."""
    # Create one test entity
    entity_data = EntitySchema(
        title="Entity1",
        entity_type="test",
        summary="Test entity",
        observations=[],
    )
    await entity_service.create_entity(entity_data)

    # Try to open two nodes, one exists, one doesn't
    permalinks = [entity_data.permalink, "type1/non_existent"]
    found = await entity_service.get_entities_by_permalinks(permalinks)

    assert len(found) == 1
    assert found[0].title == "Entity1"


async def test_delete_entities_by_permalinks(entity_service: EntityService):
    """Test deleting multiple entities by path IDs."""
    # Create test entities
    entity1_data = EntitySchema(
        title="Entity1",
        entity_type="test",
        summary="First entity",
        observations=[],
    )
    entity2_data = EntitySchema(
        title="Entity2",
        entity_type="test",
        summary="Second entity",
        observations=[],
    )
    await entity_service.create_entity(entity1_data)
    await entity_service.create_entity(entity2_data)

    # Delete by path IDs
    permalinks = [entity1_data.permalink, entity2_data.permalink]
    result = await entity_service.delete_entities(permalinks)
    assert result is True

    # Verify both are deleted
    for permalink in permalinks:
        with pytest.raises(EntityNotFoundError):
            await entity_service.get_by_permalink(permalink)


async def test_delete_entities_empty_input(entity_service: EntityService):
    """Test deleting entities with empty path ID list."""
    result = await entity_service.delete_entities([])
    assert result is True


async def test_delete_entities_none_found(entity_service: EntityService):
    """Test deleting non-existent entities by path IDs."""
    permalinks = ["type1/NonExistent1", "type2/NonExistent2"]
    result = await entity_service.delete_entities(permalinks)
    assert result is True


@pytest.mark.asyncio
async def test_get_entity_path(entity_service: EntityService):
    """Should generate correct filesystem path for entity."""
    entity = EntityModel(
        id=1,
        permalink="test-entity",
        title="test-entity",
        entity_type="test",
        summary="Test entity",
    )
    path = entity_service.file_service.get_entity_path(entity)
    assert path == Path(entity_service.file_service.base_path / "test-entity.md")


@pytest.mark.asyncio
async def test_update_knowledge_entity_summary(
    entity_service: EntityService, file_service: FileService
):
    """Should update knowledge entity description and write to file."""
    # Create test entity
    entity = await entity_service.create_entity(
        EntitySchema(
            title="test",
            entity_type="test",
            summary="Test entity",
            entity_metadata={"status": "draft"},
        )
    )

    # Update description
    updated = await entity_service.update_entity(entity.permalink, summary="Updated description")

    # Verify file has new description but preserved metadata
    file_path = file_service.get_entity_path(updated)
    content, _ = await file_service.read_file(file_path)

    assert "Updated description" in content

    # Verify metadata was preserved
    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["status"] == "draft"


@pytest.mark.asyncio
async def test_update_note_entity_content(entity_service: EntityService, file_service: FileService):
    """Should update note content directly."""
    # Create test entity
    entity = await entity_service.create_entity(
        EntitySchema(
            title="test",
            entity_type="note",
            summary="Test note",
            entity_metadata={"status": "draft"},
        )
    )

    # Update content
    new_content = "# Updated Content\n\nThis is new content."
    updated = await entity_service.update_entity(entity.permalink, content=new_content)

    # Verify file has new content but preserved metadata
    file_path = file_service.get_entity_path(updated)
    content, _ = await file_service.read_file(file_path)

    assert "# Updated Content" in content
    assert "This is new content" in content

    # Verify metadata was preserved
    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["status"] == "draft"


@pytest.mark.asyncio
async def test_update_entity_name(entity_service: EntityService, file_service: FileService):
    """Should update entity name in both DB and frontmatter."""
    # Create test entity
    entity = await entity_service.create_entity(
        EntitySchema(
            title="test",
            entity_type="test",
            summary="Test entity",
            entity_metadata={"status": "draft"},
        )
    )

    # Update name
    updated = await entity_service.update_entity(entity.permalink, title="new-name")

    # Verify name was updated in DB
    assert updated.title == "new-name"

    # Verify frontmatter was updated in file
    file_path = file_service.get_entity_path(updated)
    content, _ = await file_service.read_file(file_path)

    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["id"] == entity.permalink

    # And verify content uses new name for title
    assert "# new-name" in content
