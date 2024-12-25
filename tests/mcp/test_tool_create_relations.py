"""Tests for create_relations MCP tool."""

import pytest
import httpx
from typing import List

from basic_memory.mcp.tools import create_entities, create_relations
from basic_memory.schemas.base import Relation
from basic_memory.schemas.response import EntityListResponse


@pytest.mark.asyncio
async def test_create_basic_relation(client):
    """Test creating a simple relation between two entities."""
    # First create test entities
    await create_entities([
        {"name": "SourceEntity", "entity_type": "test"},
        {"name": "TargetEntity", "entity_type": "test"}
    ])

    # Create relation between them
    result = await create_relations([{
        "from_id": "test/source_entity",
        "to_id": "test/target_entity",
        "relation_type": "depends_on"
    }])

    assert len(result.entities) == 2
    
    # Find source and target entities
    source = next(e for e in result.entities if e.path_id == "test/source_entity")
    target = next(e for e in result.entities if e.path_id == "test/target_entity")
    
    # Both entities should have the relation for bi-directional navigation
    assert len(source.relations) == 1
    assert len(target.relations) == 1

    # Source's relation shows it depends_on target
    source_relation = source.relations[0]
    assert source_relation.from_id == "test/source_entity"
    assert source_relation.to_id == "test/target_entity"
    assert source_relation.relation_type == "depends_on"

    # Target's relation is the same, allowing backwards traversal
    target_relation = target.relations[0]
    assert target_relation.from_id == "test/source_entity"
    assert target_relation.to_id == "test/target_entity"
    assert target_relation.relation_type == "depends_on"


@pytest.mark.asyncio
async def test_create_relation_with_context(client):
    """Test creating a relation with context."""
    # Create test entities
    await create_entities([
        {"name": "Source", "entity_type": "test"},
        {"name": "Target", "entity_type": "test"}
    ])

    result = await create_relations([{
        "from_id": "test/source",
        "to_id": "test/target",
        "relation_type": "implements",
        "context": "Implementation details"
    }])

    source = next(e for e in result.entities if e.path_id == "test/source")
    target = next(e for e in result.entities if e.path_id == "test/target")

    # Both entities should have the relation with context
    assert len(source.relations) == 1
    assert len(target.relations) == 1
    assert source.relations[0].context == "Implementation details"
    assert target.relations[0].context == "Implementation details"


@pytest.mark.asyncio
async def test_create_multiple_relations(client):
    """Test creating multiple relations in one request."""
    # Create test entities
    await create_entities([
        {"name": "Entity1", "entity_type": "test"},
        {"name": "Entity2", "entity_type": "test"},
        {"name": "Entity3", "entity_type": "test"}
    ])

    relations = [
        {
            "from_id": "test/entity1",
            "to_id": "test/entity2",
            "relation_type": "connects_to"
        },
        {
            "from_id": "test/entity2",
            "to_id": "test/entity3",
            "relation_type": "depends_on"
        }
    ]

    result = await create_relations(relations)
    
    # Should return all involved entities
    assert len(result.entities) == 3
    
    # Get entities
    entity1 = next(e for e in result.entities if e.path_id == "test/entity1")
    entity2 = next(e for e in result.entities if e.path_id == "test/entity2")
    entity3 = next(e for e in result.entities if e.path_id == "test/entity3")
    
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
    await create_entities([
        {"name": "Service", "entity_type": "test"},
        {"name": "Database", "entity_type": "test"}
    ])

    # Create relations in both directions
    result = await create_relations([
        {
            "from_id": "test/service",
            "to_id": "test/database",
            "relation_type": "depends_on"
        },
        {
            "from_id": "test/database",
            "to_id": "test/service",
            "relation_type": "supports"
        }
    ])

    service = next(e for e in result.entities if e.path_id == "test/service")
    database = next(e for e in result.entities if e.path_id == "test/database")

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
    """Test creating a relation with non-existent entity fails with 404."""
    # Create only one of the needed entities
    await create_entities([
        {"name": "RealEntity", "entity_type": "test"}
    ])

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await create_relations([{
            "from_id": "test/real_entity",
            "to_id": "test/non_existent_entity",
            "relation_type": "depends_on"
        }])
    
    # Should be a 404 Not Found
    assert exc_info.value.response.status_code == 404


@pytest.mark.asyncio
async def test_create_duplicate_relation(client):
    """Test attempting to create a duplicate relation."""
    # Create test entities
    await create_entities([
        {"name": "Source", "entity_type": "test"},
        {"name": "Target", "entity_type": "test"}
    ])

    # Create initial relation
    relation = {
        "from_id": "test/source",
        "to_id": "test/target",
        "relation_type": "connects_to"
    }
    
    # Create first relation
    first_result = await create_relations([relation])
    assert len(first_result.entities[0].relations) == 1

    # Attempt to create same relation again
    second_result = await create_relations([relation])
    # Should not add duplicate relation
    assert len(second_result.entities[0].relations) == 1