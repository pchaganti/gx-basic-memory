"""Tests for get_entity MCP tool."""

import pytest

from basic_memory.mcp.tools.knowledge import get_entity, create_entities
from basic_memory.schemas.base import Entity, ObservationCategory
from basic_memory.schemas.request import CreateEntityRequest
from basic_memory.services.exceptions import EntityNotFoundError


@pytest.mark.asyncio
async def test_get_basic_entity(client):
    """Test retrieving a basic entity."""
    # First create an entity
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                title="TestEntity",
                entity_type="test",
                summary="A test entity",
                observations=["First observation"],
            )
        ]
    )
    create_result = await create_entities(entity_request)
    permalink = create_result.entities[0].permalink

    # Get the entity without content
    entity = await get_entity(permalink)

    # Verify entity details
    assert entity.title == "TestEntity"
    assert entity.entity_type == "test"
    assert entity.permalink == "test_entity"
    assert entity.summary == "A test entity"

    # Check observations
    assert len(entity.observations) == 1
    obs = entity.observations[0]
    assert obs.content == "First observation"
    assert obs.category == ObservationCategory.NOTE



@pytest.mark.asyncio
async def test_get_entity_with_relations(client):
    """Test retrieving an entity with relations."""
    # Create two entities that will have a relation
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="SourceEntity", entity_type="test"),
            Entity(title="TargetEntity", entity_type="test"),
        ]
    )
    await create_entities(entity_request)

    # Create relation between them (using the earlier tested create_relations)
    from basic_memory.mcp.tools.knowledge import create_relations
    from basic_memory.schemas.request import CreateRelationsRequest
    from basic_memory.schemas.base import Relation

    relation_request = CreateRelationsRequest(
        relations=[
            Relation(from_id="source_entity", to_id="target_entity", relation_type="depends_on")
        ]
    )
    await create_relations(relation_request)

    # Get and verify source entity without content
    source = await get_entity("source_entity")
    assert len(source.relations) == 1
    relation = source.relations[0]
    assert relation.to_id == "target_entity"
    assert relation.relation_type == "depends_on"


@pytest.mark.asyncio
async def test_get_entity_with_categorized_observations(client):
    """Test retrieving an entity with observations in different categories."""
    # Create entity with categorized observations
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="TestEntity", entity_type="test", summary="Test entity with categories")
        ]
    )
    result = await create_entities(entity_request)
    permalink = result.entities[0].permalink

    # Add observations with different categories
    from basic_memory.mcp.tools.knowledge import add_observations
    from basic_memory.schemas.request import AddObservationsRequest, ObservationCreate

    obs_request = AddObservationsRequest(
        permalink=permalink,
        observations=[
            ObservationCreate(content="Technical detail", category=ObservationCategory.TECH),
            ObservationCreate(content="Design decision", category=ObservationCategory.DESIGN),
            ObservationCreate(content="Feature note", category=ObservationCategory.FEATURE),
        ],
    )
    await add_observations(obs_request)

    # Get and verify entity without content
    entity = await get_entity(permalink)
    assert len(entity.observations) == 3
    categories = {obs.category for obs in entity.observations}
    assert ObservationCategory.TECH in categories
    assert ObservationCategory.DESIGN in categories
    assert ObservationCategory.FEATURE in categories


@pytest.mark.asyncio
async def test_get_nonexistent_entity(client):
    """Test attempting to get a non-existent entity."""
    with pytest.raises(EntityNotFoundError):
        await get_entity("test/nonexistent")
