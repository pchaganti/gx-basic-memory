"""Tests for KnowledgeService."""

from pathlib import Path
from typing import List

import pytest

from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Entity as EntitySchema, Relation as RelationSchema
from basic_memory.services import EntityService
from basic_memory.services.exceptions import EntityNotFoundError, FileOperationError
from basic_memory.services.knowledge import KnowledgeService


@pytest.mark.asyncio
async def test_get_entity_path(knowledge_service: KnowledgeService):
    """Should generate correct filesystem path for entity."""
    entity = EntityModel(id=1, name="test-entity", entity_type="concept", description="Test entity")
    path = knowledge_service.get_entity_path(entity)
    assert path == Path(knowledge_service.base_path / "knowledge/concept/test-entity.md")


@pytest.mark.asyncio
async def test_create_entity(knowledge_service: KnowledgeService, test_project_path: Path):
    """Should create entity in DB and write file correctly."""
    # Setup
    entity = EntitySchema(name="test-entity", entity_type="concept", description="Test entity")

    # Execute
    created = await knowledge_service.create_entity(entity)

    # Verify DB entity
    assert created.name == entity.name
    assert created.entity_type == entity.entity_type
    assert created.description == entity.description
    assert created.checksum is not None

    # Verify file was written
    file_path = knowledge_service.get_entity_path(created)
    assert await knowledge_service.file_service.exists(file_path)


@pytest.mark.asyncio
async def test_create_multiple_entities(knowledge_service: KnowledgeService):
    """Should create multiple entities successfully."""
    entities = [
        EntitySchema(name=f"entity-{i}", entity_type="test", description=f"Test entity {i}")
        for i in range(3)
    ]

    created = await knowledge_service.create_entities(entities)
    assert len(created) == 3

    for i, entity in enumerate(created):
        assert entity.name == f"entity-{i}"
        file_path = knowledge_service.get_entity_path(entity)
        assert await knowledge_service.file_service.exists(file_path)


@pytest.mark.asyncio
async def test_create_relations(knowledge_service: KnowledgeService, entity_service: EntityService):
    """Should create relations and update related entity files."""
    # Create test entities
    entity1 = await knowledge_service.create_entity(
        EntitySchema(name="entity1", entity_type="test", description="Test entity 1")
    )
    entity2 = await knowledge_service.create_entity(
        EntitySchema(name="entity2", entity_type="test", description="Test entity 2")
    )

    # Create relation
    relations = [
        RelationSchema(
            from_id=entity1.id,
            to_id=entity2.id,
            relation_type="test_relation",
            context="Test context",
        )
    ]

    created = await knowledge_service.create_relations(relations)
    assert len(created) == 1

    # Verify relation was created
    relation = created[0]
    assert relation.from_id == entity1.id
    assert relation.to_id == entity2.id
    assert relation.relation_type == "test_relation"

    # Verify files were updated
    for entity_id in [entity1.id, entity2.id]:
        entity = await entity_service.get_entity(entity_id)
        file_path = knowledge_service.get_entity_path(entity)
        content, _ = await knowledge_service.file_service.read_file(file_path)
        assert "test_relation" in content


@pytest.mark.asyncio
async def test_add_observations(knowledge_service: KnowledgeService):
    """Should add observations and update entity file."""
    # Create test entity
    entity = await knowledge_service.create_entity(
        EntitySchema(name="test", entity_type="test", description="Test entity")
    )

    # Add observations
    observations = ["Test observation 1", "Test observation 2"]
    updated = await knowledge_service.add_observations(entity.id, observations, "Test context")

    # Verify observations in DB
    assert len(updated.observations) == 2
    assert updated.observations[0].content == "Test observation 1"
    assert updated.observations[1].content == "Test observation 2"

    # Verify file was updated
    file_path = knowledge_service.get_entity_path(updated)
    content, _ = await knowledge_service.file_service.read_file(file_path)
    for obs in observations:
        assert obs in content


@pytest.mark.asyncio
async def test_delete_entity(knowledge_service: KnowledgeService):
    """Should delete entity and its file."""
    # Create test entity
    entity = await knowledge_service.create_entity(
        EntitySchema(name="test", entity_type="test", description="Test entity")
    )
    file_path = knowledge_service.get_entity_path(entity)

    # Verify file exists
    assert await knowledge_service.file_service.exists(file_path)

    # Delete entity
    success = await knowledge_service.delete_entity(entity.id)
    assert success

    # Verify file was deleted
    assert not await knowledge_service.file_service.exists(file_path)

    # Verify entity was deleted from DB
    with pytest.raises(EntityNotFoundError):
        await knowledge_service.entity_service.get_entity(entity.id)


@pytest.mark.asyncio
async def test_delete_multiple_entities(knowledge_service: KnowledgeService):
    """Should delete multiple entities and their files."""
    # Create test entities
    entities = []
    for i in range(3):
        entity = await knowledge_service.create_entity(
            EntitySchema(name=f"test-{i}", entity_type="test", description=f"Test entity {i}")
        )
        entities.append(entity)

    # Delete entities
    success = await knowledge_service.delete_entities([e.id for e in entities])
    assert success

    # Verify files were deleted
    for entity in entities:
        file_path = knowledge_service.get_entity_path(entity)
        assert not await knowledge_service.file_service.exists(file_path)
        with pytest.raises(EntityNotFoundError):
            await knowledge_service.entity_service.get_entity(entity.id)


@pytest.mark.asyncio
async def test_handle_file_operation_errors(knowledge_service: KnowledgeService, monkeypatch):
    """Should handle file operation errors gracefully."""

    async def mock_write_file(*args):
        raise FileOperationError("Test error")

    monkeypatch.setattr(knowledge_service.file_service, "write_file", mock_write_file)

    with pytest.raises(FileOperationError):
        await knowledge_service.create_entity(
            EntitySchema(name="test", entity_type="test", description="Test entity")
        )


@pytest.mark.asyncio
async def test_entity_not_found_error(knowledge_service: KnowledgeService):
    """Should raise EntityNotFoundError for non-existent entity."""
    with pytest.raises(EntityNotFoundError):
        await knowledge_service.add_observations(999, ["Test observation"])


@pytest.mark.asyncio
async def test_cleanup_on_creation_failure(knowledge_service: KnowledgeService, monkeypatch):
    """Should clean up DB entity if file write fails."""
    entity_ids: List[int] = []

    # Capture created entity ID
    original_create = knowledge_service.entity_service.create_entity

    async def mock_create_entity(*args, **kwargs):
        entity = await original_create(*args, **kwargs)
        entity_ids.append(entity.id)
        return entity

    # Force file write to fail
    async def mock_write_file(*args):
        raise FileOperationError("Test error")

    monkeypatch.setattr(knowledge_service.entity_service, "create_entity", mock_create_entity)
    monkeypatch.setattr(knowledge_service.file_service, "write_file", mock_write_file)

    # Attempt creation (should fail)
    with pytest.raises(FileOperationError):
        await knowledge_service.create_entity(
            EntitySchema(name="test", entity_type="test", description="Test entity")
        )

    # Verify entity was cleaned up
    assert len(entity_ids) == 1
    with pytest.raises(EntityNotFoundError):
        await knowledge_service.entity_service.get_entity(entity_ids[0])


@pytest.mark.asyncio
async def test_skip_failed_batch_operations(knowledge_service: KnowledgeService):
    """Should continue processing batch operations if some fail."""
    entities = [
        EntitySchema(name="test-1", entity_type="test", description="Test entity 1"),
        EntitySchema(name="test-1", entity_type="test", description="Duplicate name - should fail"),
        EntitySchema(name="test-2", entity_type="test", description="Test entity 2"),
    ]

    created = await knowledge_service.create_entities(entities)
    assert len(created) == 2  # Middle one should fail but not stop processing

    # Verify first and last were created
    names = [e.name for e in created]
    assert "test-1" in names
    assert "test-2" in names


@pytest.mark.asyncio
async def test_update_relations_in_files(knowledge_service: KnowledgeService):
    """Should update both entity files when creating relations."""
    # Create test entities
    entity1 = await knowledge_service.create_entity(
        EntitySchema(name="source", entity_type="test", description="Source entity")
    )
    entity2 = await knowledge_service.create_entity(
        EntitySchema(name="target", entity_type="test", description="Target entity")
    )

    # Create relation
    relations = [
        RelationSchema(
            from_id=entity1.id,
            to_id=entity2.id,
            relation_type="connects_to",
            context="Test connection",
        )
    ]

    await knowledge_service.create_relations(relations)

    # Verify both files contain relation
    for entity in [entity1, entity2]:
        file_path = knowledge_service.get_entity_path(entity)
        content, _ = await knowledge_service.file_service.read_file(file_path)
        assert "connects_to" in content

    # Source should show outgoing relation
    content, _ = await knowledge_service.file_service.read_file(
        knowledge_service.get_entity_path(entity1)
    )
    assert "target" in content

    # Target should show incoming relation
    content, _ = await knowledge_service.file_service.read_file(
        knowledge_service.get_entity_path(entity2)
    )
    assert "source" in content
