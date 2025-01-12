"""Tests for create_relations MCP tool."""

import pytest

from basic_memory.mcp.tools.knowledge import create_entities, create_relations
from basic_memory.schemas.base import Relation, Entity
from basic_memory.schemas.request import CreateEntityRequest, CreateRelationsRequest


@pytest.mark.asyncio
async def test_create_basic_relation(client):
    """Test creating a simple relation between two entities."""
    # First create test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="SourceEntity", entity_type="test"),
            Entity(title="TargetEntity", entity_type="test"),
        ]
    )
    await create_entities(entity_request)

    # Create relation between them
    relation_request = CreateRelationsRequest(
        relations=[
            Relation(from_id="source_entity", to_id="target_entity", relation_type="depends_on")
        ]
    )
    result = await create_relations(relation_request)

    assert len(result.entities) == 2

    # Find source and target entities
    source = next(e for e in result.entities if e.path_id == "source_entity")
    target = next(e for e in result.entities if e.path_id == "target_entity")

    # Both entities should have the relation for bi-directional navigation
    assert len(source.relations) == 1
    assert len(target.relations) == 1

    # Source's relation shows it depends_on target
    source_relation = source.relations[0]
    assert source_relation.from_id == "source_entity"
    assert source_relation.to_id == "target_entity"
    assert source_relation.relation_type == "depends_on"

    # Target's relation is the same, allowing backwards traversal
    target_relation = target.relations[0]
    assert target_relation.from_id == "source_entity"
    assert target_relation.to_id == "target_entity"
    assert target_relation.relation_type == "depends_on"


@pytest.mark.asyncio
async def test_create_relation_with_context(client):
    """Test creating a relation with context."""
    # Create test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="Source", entity_type="test"),
            Entity(title="Target", entity_type="test"),
        ]
    )
    await create_entities(entity_request)

    relation_request = CreateRelationsRequest(
        relations=[
            Relation(
                from_id="source",
                to_id="target",
                relation_type="implements",
                context="Implementation details",
            )
        ]
    )
    result = await create_relations(relation_request)

    source = next(e for e in result.entities if e.path_id == "source")
    target = next(e for e in result.entities if e.path_id == "target")

    # Both entities should have the relation with context
    assert len(source.relations) == 1
    assert len(target.relations) == 1
    assert source.relations[0].context == "Implementation details"
    assert target.relations[0].context == "Implementation details"


@pytest.mark.asyncio
async def test_create_multiple_relations(client):
    """Test creating multiple relations in one request."""
    # Create test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="Entity1", entity_type="test"),
            Entity(title="Entity2", entity_type="test"),
            Entity(title="Entity3", entity_type="test"),
        ]
    )
    await create_entities(entity_request)

    relation_request = CreateRelationsRequest(
        relations=[
            Relation(from_id="entity1", to_id="entity2", relation_type="connects_to"),
            Relation(from_id="entity2", to_id="entity3", relation_type="depends_on"),
        ]
    )
    result = await create_relations(relation_request)

    # Should return all involved entities
    assert len(result.entities) == 3

    # Get entities
    entity1 = next(e for e in result.entities if e.path_id == "entity1")
    entity2 = next(e for e in result.entities if e.path_id == "entity2")
    entity3 = next(e for e in result.entities if e.path_id == "entity3")

    # Entity1 and Entity2 should share the connects_to relation
    assert len(entity1.relations) == 1
    assert len(entity2.relations) == 2  # Has both relations
    assert len(entity3.relations) == 1

    # Verify relation types
    assert any(r.relation_type == "connects_to" for r in entity1.relations)
    assert any(r.relation_type == "connects_to" for r in entity2.relations)
    assert any(r.relation_type == "depends_on" for r in entity2.relations)
    assert any(r.relation_type == "depends_on" for r in entity3.relations)


@pytest.mark.asyncio
async def test_create_bidirectional_relations(client):
    """Test creating explicit relations in both directions between entities."""
    # Create test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="Service", entity_type="test"),
            Entity(title="Database", entity_type="test"),
        ]
    )
    await create_entities(entity_request)

    # Create relations in both directions
    relation_request = CreateRelationsRequest(
        relations=[
            Relation(from_id="service", to_id="database", relation_type="depends_on"),
            Relation(from_id="database", to_id="service", relation_type="supports"),
        ]
    )
    result = await create_relations(relation_request)

    service = next(e for e in result.entities if e.path_id == "service")
    database = next(e for e in result.entities if e.path_id == "database")

    # Each entity should have both relations for full navigation
    assert len(service.relations) == 2
    assert len(database.relations) == 2

    # Verify relation types exist in both directions
    service_relations = {r.relation_type for r in service.relations}
    database_relations = {r.relation_type for r in database.relations}
    assert "depends_on" in service_relations
    assert "supports" in service_relations
    assert "depends_on" in database_relations
    assert "supports" in database_relations


@pytest.mark.asyncio
async def test_create_relation_with_invalid_entity(client):
    """Test creating a relation with non-existent entity fails."""
    # Create only one of the needed entities
    entity_request = CreateEntityRequest(entities=[Entity(title="RealEntity", entity_type="test")])
    await create_entities(entity_request)

    relation_request = CreateRelationsRequest(
        relations=[
            Relation(from_id="real_entity", to_id="non_existent_entity", relation_type="depends_on")
        ]
    )

    # Should get empty result since relation creation failed
    result = await create_relations(relation_request)
    assert len(result.entities) == 0


@pytest.mark.asyncio
async def test_create_duplicate_relation(client):
    """Test attempting to create a duplicate relation."""
    # Create test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="Source", entity_type="test"),
            Entity(title="Target", entity_type="test"),
        ]
    )
    await create_entities(entity_request)

    # Create relation
    relation = Relation(from_id="source", to_id="target", relation_type="connects_to")
    relation_request = CreateRelationsRequest(relations=[relation])

    # Create first relation
    first_result = await create_relations(relation_request)
    assert len(first_result.entities) == 2
    assert len(first_result.entities[0].relations) == 1

    # Attempt to create same relation again
    second_result = await create_relations(relation_request)
    # Current behavior: No entities returned when duplicate relation fails
    assert len(second_result.entities) == 0
