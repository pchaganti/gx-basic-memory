"""Tests for RelationService."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory.models import Entity, Relation
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.services.relation_service import RelationService



@pytest_asyncio.fixture
async def test_entities(
    session_maker: async_sessionmaker[AsyncSession],
) -> tuple[Entity, Entity]:
    """Create two test entities."""
    async with session_maker() as session:
        entity1 = Entity(
            name="test_entity_1",
            entity_type="test",
            path_id="test/test_entity_1",
            file_path="test/test_entity_1.md",
            description="Test entity 1",
        )
        entity2 = Entity(
            name="test_entity_2",
            entity_type="test",
            path_id="test/test_entity_2",
            file_path="test/test_entity_2.md",
            description="Test entity 2",
        )
        session.add_all([entity1, entity2])
        await session.commit()
        return entity1, entity2


@pytest.mark.asyncio
async def test_create_relation(
    relation_service: RelationService, test_entities: tuple[Entity, Entity]
):
    """Test creating a basic relation between two entities."""
    entity1, entity2 = test_entities

    relation_data = Relation(from_id=entity1.id, to_id=entity2.id, relation_type="test_relation")

    relation = await relation_service.create_relation(relation_data)

    assert relation.from_id == entity1.id
    assert relation.to_id == entity2.id
    assert relation.relation_type == "test_relation"


@pytest.mark.asyncio
async def test_create_relations(
    relation_service: RelationService, test_entities: tuple[Entity, Entity]
):
    """Test creating a basic relation between two entities."""
    entity1, entity2 = test_entities

    relation_data = [
        Relation(from_id=entity1.id, to_id=entity2.id, relation_type="type_0"),
        Relation(from_id=entity1.id, to_id=entity2.id, relation_type="type_1"),
    ]

    relations = await relation_service.create_relations(relation_data)
    assert len(relations) == 2
    relation0 = relations[0]
    assert relation0.from_id == entity1.id
    assert relation0.to_id == entity2.id
    assert relation0.relation_type == "type_0"

    relation1 = relations[1]
    assert relation1.from_id == entity1.id
    assert relation1.to_id == entity2.id
    assert relation1.relation_type == "type_1"


@pytest.mark.asyncio
async def test_create_relation_with_context(
    relation_service: RelationService, test_entities: tuple[Entity, Entity]
):
    """Test creating a relation with context information."""
    entity1, entity2 = test_entities

    relation_data = Relation(
        from_id=entity1.id, to_id=entity2.id, relation_type="test_relation", context="test context"
    )

    relation = await relation_service.create_relation(relation_data)

    assert relation.context == "test context"


@pytest.mark.asyncio
async def test_delete_relation(
    relation_service: RelationService, test_entities: tuple[Entity, Entity]
):
    """Test deleting a relation between entities."""
    entity1, entity2 = test_entities

    # Create a relation first
    relation_data = Relation(from_id=entity1.id, to_id=entity2.id, relation_type="test_relation")
    await relation_service.create_relation(relation_data)

    # Delete the relation
    result = await relation_service.delete_relation(entity1, entity2, "test_relation")

    assert result is True


@pytest.mark.asyncio
async def test_delete_nonexistent_relation(
    relation_service: RelationService, test_entities: tuple[Entity, Entity]
):
    """Test trying to delete a relation that doesn't exist."""
    entity1, entity2 = test_entities

    result = await relation_service.delete_relation(entity1, entity2, "nonexistent_relation")

    assert result is False


@pytest.mark.asyncio
async def test_delete_relations_by_criteria(
    relation_service: RelationService, test_entities: tuple[Entity, Entity]
):
    """Test deleting relations by criteria."""
    entity1, entity2 = test_entities

    # Create test relations
    relation1 = Relation(from_id=entity1.id, to_id=entity2.id, relation_type="relation1")
    await relation_service.create_relation(relation1)
    relation2 = Relation(from_id=entity1.id, to_id=entity2.id, relation_type="relation2")
    await relation_service.create_relation(relation2)

    # Delete relations matching criteria
    result = await relation_service.delete_relations([relation1, relation2])

    assert result == 2
