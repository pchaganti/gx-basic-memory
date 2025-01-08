"""Tests for KnowledgeService."""

from pathlib import Path

import pytest
import yaml

from basic_memory.models import Entity as EntityModel
from basic_memory.models.knowledge import ObservationCategory
from basic_memory.schemas import Entity as EntitySchema, Relation as RelationSchema
from basic_memory.schemas.request import ObservationCreate
from basic_memory.services import EntityService
from basic_memory.services.knowledge import KnowledgeService


@pytest.mark.asyncio
async def test_get_entity_path(knowledge_service: KnowledgeService):
    """Should generate correct filesystem path for entity."""
    entity = EntityModel(
        id=1,
        path_id="test-entity",
        name="test-entity",
        entity_type="test",
        summary="Test entity",
    )
    path = knowledge_service.get_entity_path(entity)
    assert path == Path(knowledge_service.base_path / "test-entity.md")


@pytest.mark.asyncio
async def test_create_entity(knowledge_service: KnowledgeService):
    """Should create entity in DB and write file correctly."""
    # Setup
    entity_schema = EntitySchema(name="test-entity", entity_type="test", summary="Test entity")

    # Execute
    created = await knowledge_service.create_entity(entity_schema)

    # Verify DB entity
    assert created.name == entity_schema.name
    assert created.entity_type == entity_schema.entity_type
    assert created.summary == entity_schema.summary
    assert created.checksum is not None
    assert created.path_id == "test_entity"
    assert created.file_path == "test_entity.md"

    # Verify file was written
    file_path = knowledge_service.get_entity_path(created)
    assert await knowledge_service.file_exists(file_path)

    file_content, _ = await knowledge_service.read_file(file_path)
    _, frontmatter, doc_content = file_content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)

    # Verify frontmatter contents
    assert metadata["id"] == entity_schema.path_id
    assert metadata["type"] == entity_schema.entity_type
    assert "created" in metadata
    assert "modified" in metadata


@pytest.mark.asyncio
async def test_create_multiple_entities(knowledge_service: KnowledgeService):
    """Should create multiple entities successfully."""
    entities = [
        EntitySchema(name=f"entity-{i}", entity_type="test", summary=f"Test entity {i}")
        for i in range(3)
    ]

    created = await knowledge_service.create_entities(entities)
    assert len(created) == 3

    for i, entity in enumerate(created):
        assert entity.name == f"entity-{i}"
        file_path = knowledge_service.get_entity_path(entity)
        assert await knowledge_service.file_exists(file_path)


@pytest.mark.asyncio
async def test_create_relations(knowledge_service: KnowledgeService, entity_service: EntityService):
    """Should create relations and update related entity files."""
    # Create test entities
    entity1 = await knowledge_service.create_entity(
        EntitySchema(name="entity1", entity_type="test", summary="Test entity 1")
    )
    entity2 = await knowledge_service.create_entity(
        EntitySchema(name="entity2", entity_type="test", summary="Test entity 2")
    )

    # Create relation
    relations = [
        RelationSchema(
            from_id=entity1.path_id,
            to_id=entity2.path_id,
            relation_type="test_relation",
            context="Test context",
        )
    ]

    updated_entities = await knowledge_service.create_relations(relations)
    assert len(updated_entities) == 2

    # Verify outgoing relation is updated
    found = await entity_service.get_by_path_id(entity1.path_id)
    file_path = knowledge_service.get_entity_path(found)
    content, _ = await knowledge_service.read_file(file_path)
    assert "test_relation" in content

    # Verify other entity file is not updated
    found = await entity_service.get_by_path_id(entity2.path_id)
    file_path = knowledge_service.get_entity_path(found)
    content, _ = await knowledge_service.read_file(file_path)
    assert "test_relation" not in content


@pytest.mark.asyncio
async def test_update_knowledge_entity_description(knowledge_service: KnowledgeService):
    """Should update knowledge entity description and write to file."""
    # Create test entity
    entity = await knowledge_service.create_entity(
        EntitySchema(
            name="test",
            entity_type="test",
            summary="Test entity",
            entity_metadata={"status": "draft"},
        )
    )

    # Update description
    updated = await knowledge_service.update_entity(
        entity.path_id, summary="Updated description"
    )

    # Verify file has new description but preserved metadata
    file_path = knowledge_service.get_entity_path(updated)
    content, _ = await knowledge_service.read_file(file_path)

    assert "Updated description" in content

    # Verify metadata was preserved
    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["status"] == "draft"


@pytest.mark.asyncio
async def test_update_note_entity_content(knowledge_service: KnowledgeService):
    """Should update note content directly."""
    # Create test entity
    entity = await knowledge_service.create_entity(
        EntitySchema(
            name="test",
            entity_type="note",
            summary="Test note",
            entity_metadata={"status": "draft"},
        )
    )

    # Update content
    new_content = "# Updated Content\n\nThis is new content."
    updated = await knowledge_service.update_entity(entity.path_id, content=new_content)

    # Verify file has new content but preserved metadata
    file_path = knowledge_service.get_entity_path(updated)
    content, _ = await knowledge_service.read_file(file_path)

    assert "# Updated Content" in content
    assert "This is new content" in content

    # Verify metadata was preserved
    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["status"] == "draft"


@pytest.mark.asyncio
async def test_update_entity_name(knowledge_service: KnowledgeService):
    """Should update entity name in both DB and frontmatter."""
    # Create test entity
    entity = await knowledge_service.create_entity(
        EntitySchema(
            name="test",
            entity_type="test",
            summary="Test entity",
            entity_metadata={"status": "draft"},
        )
    )

    # Update name
    updated = await knowledge_service.update_entity(entity.path_id, name="new-name")

    # Verify name was updated in DB
    assert updated.name == "new-name"

    # Verify frontmatter was updated in file
    file_path = knowledge_service.get_entity_path(updated)
    content, _ = await knowledge_service.read_file(file_path)

    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["id"] == entity.path_id

    # And verify content uses new name for title
    assert "# new-name" in content


@pytest.mark.asyncio
async def test_update_entity_type_note_to_knowledge(knowledge_service: KnowledgeService):
    """Should update entity from note to knowledge type."""
    # Create test entity as note
    initial_content = "# Test Note\n\nThis is a test note."
    entity = await knowledge_service.create_entity(
        EntitySchema(
            name="test",
            entity_type="note",
            summary="Test note",
            entity_metadata={"status": "draft"},
        )
    )

    # First update with some content as a note
    await knowledge_service.update_entity(entity.path_id, content=initial_content)

    # Then update to knowledge type
    updated = await knowledge_service.update_entity(entity.path_id, entity_type="test")

    # Verify type was updated in DB
    assert updated.entity_type == "test"

    # Verify frontmatter was updated
    file_path = knowledge_service.get_entity_path(updated)
    content, _ = await knowledge_service.read_file(file_path)

    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["type"] == "test"

    # Verify content format changed to knowledge style (structured)
    assert "# test" in content
    assert "Test note" in content  # Description preserved


@pytest.mark.asyncio
async def test_update_entity_type_knowledge_to_note(knowledge_service: KnowledgeService):
    """Should update entity from knowledge to note type."""
    # Create test entity as knowledge
    entity = await knowledge_service.create_entity(
        EntitySchema(
            name="test",
            entity_type="test",
            summary="Test knowledge entity",
            entity_metadata={"status": "draft"},
        )
    )

    # Add some observations to test conversion
    observations = [
        ObservationCreate(content="Test observation", category=ObservationCategory.TECH)
    ]
    entity = await knowledge_service.add_observations(entity.path_id, observations)

    # Update to note type with new content
    new_content = "# Test Note\n\nConverted to note format."
    updated = await knowledge_service.update_entity(
        entity.path_id, entity_type="note", content=new_content
    )

    # Verify type was updated in DB
    assert updated.entity_type == "note"

    # Verify frontmatter was updated
    file_path = knowledge_service.get_entity_path(updated)
    content, _ = await knowledge_service.read_file(file_path)

    _, frontmatter, _ = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["type"] == "note"

    # Verify content changed to note style (direct content)
    assert "# Test Note" in content
    assert "Converted to note format" in content
    assert "Test observation" not in content  # Observations not included in note format

    # Verify metadata was preserved
    assert metadata["status"] == "draft"
