"""Tests for RelationService."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory.models import Entity as EntityModel
from basic_memory.schemas import Relation as RelationSchema
from basic_memory.services import EntityService, FileService
from basic_memory.services.relation_service import RelationService


@pytest_asyncio.fixture
async def test_entities(
    session_maker: async_sessionmaker[AsyncSession],
) -> tuple[EntityModel, EntityModel]:
    """Create two test entities."""
    async with session_maker() as session:
        entity1 = EntityModel(
            title="test_entity_1",
            entity_type="test",
            permalink="test/test-entity-1",
            file_path="test/test_entity_1.md",
            summary="Test entity 1",
            content_type="text/markdown",
        )
        entity2 = EntityModel(
            title="test_entity_2",
            entity_type="test",
            permalink="test/test-entity-2",
            file_path="test/test_entity_2.md",
            summary="Test entity 2",
            content_type="text/markdown",
        )
        session.add_all([entity1, entity2])
        await session.commit()
        return entity1, entity2


@pytest.mark.asyncio
async def test_create_relations(
    relation_service: RelationService,
    entity_service: EntityService,
    file_service: FileService,
    test_entities: tuple[EntityModel, EntityModel],
):
    """Test creating a basic relation between two entities."""
    entity1, entity2 = test_entities

    relation_data = [
        RelationSchema(
            from_id=entity1.permalink,
            to_id=entity2.permalink,
            relation_type="type_0",
            context="context_0",
        ),
        RelationSchema(
            from_id=entity1.permalink,
            to_id=entity2.permalink,
            relation_type="type_1",
            context="context_1",
        ),
    ]

    entities = await relation_service.create_relations(relation_data)

    assert len(entities) == 2

    # verify relations on e0
    relations_e0 = entities[0].outgoing_relations
    assert len(relations_e0) == 2

    assert relations_e0[0].from_id == entity1.id
    assert relations_e0[0].to_id == entity2.id
    assert relations_e0[0].relation_type == "type_0"

    assert relations_e0[1].from_id == entity1.id
    assert relations_e0[1].to_id == entity2.id
    assert relations_e0[1].relation_type == "type_1"

    # verify relations on e1
    relations_e1 = entities[1].incoming_relations
    assert len(relations_e1) == 2

    assert relations_e1[0].from_id == entity1.id
    assert relations_e1[0].to_id == entity2.id
    assert relations_e1[0].relation_type == "type_0"

    assert relations_e1[1].from_id == entity1.id
    assert relations_e1[1].to_id == entity2.id
    assert relations_e1[1].relation_type == "type_1"

    # Verify outgoing relation is updated
    found = await entity_service.get_by_permalink(entity1.permalink)
    file_path = file_service.get_entity_path(found)
    content, _ = await file_service.read_file(file_path)

    # verify relation format
    assert f"- type_0 [[{entity2.title}]] (context_0)" in content
    assert f"- type_1 [[{entity2.title}]] (context_1)" in content

    # Verify other entity file is not updated
    found = await entity_service.get_by_permalink(entity2.permalink)
    file_path = file_service.get_entity_path(found)
    content, _ = await file_service.read_file(file_path)
    assert "type_0" not in content


@pytest.mark.asyncio
async def test_delete_relation(
    relation_service: RelationService, test_entities: tuple[EntityModel, EntityModel]
):
    """Test deleting a relation between entities."""
    entity1, entity2 = test_entities

    # Create a relation first
    relation_data = RelationSchema(
        from_id=entity1.permalink, to_id=entity2.permalink, relation_type="test_relation"
    )
    await relation_service.create_relations([relation_data])

    # Delete the relation
    result = await relation_service.delete_relation(entity1, entity2, "test_relation")

    assert result is True


@pytest.mark.asyncio
async def test_delete_nonexistent_relation(
    relation_service: RelationService, test_entities: tuple[EntityModel, EntityModel]
):
    """Test trying to delete a relation that doesn't exist."""
    entity1, entity2 = test_entities

    result = await relation_service.delete_relation(entity1, entity2, "nonexistent_relation")

    assert result is False


@pytest.mark.asyncio
async def test_delete_relations_by_criteria(
    relation_service: RelationService, test_entities: tuple[EntityModel, EntityModel]
):
    """Test deleting relations by criteria."""
    entity1, entity2 = test_entities

    # Create test relations
    relation1 = RelationSchema(
        from_id=entity1.permalink, to_id=entity2.permalink, relation_type="relation1"
    )
    relation2 = RelationSchema(
        from_id=entity1.permalink, to_id=entity2.permalink, relation_type="relation2"
    )
    await relation_service.create_relations([relation1, relation2])

    # Delete relations matching criteria
    entities = await relation_service.delete_relations([relation1, relation2])

    assert len(entities) == 2
    assert len(entities[0].relations) == 0
    assert len(entities[1].relations) == 0
