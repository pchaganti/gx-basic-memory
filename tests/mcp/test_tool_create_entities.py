"""Tests for create_entities MCP tool."""

import pytest

from basic_memory.mcp.tools.knowledge import create_entities
from basic_memory.schemas.base import ObservationCategory, Entity
from basic_memory.schemas.request import CreateEntityRequest


@pytest.mark.asyncio
async def test_create_basic_entity(client):
    """Test creating a simple entity."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                title="TestEntity",
                entity_type="test",
                observations=["First observation"],
            )
        ]
    )

    result = await create_entities(request)

    # Result should be an EntityListResponse
    assert len(result.entities) == 1

    # Check the created entity
    entity = result.entities[0]
    assert entity.title == "TestEntity"
    assert entity.entity_type == "test"
    assert entity.permalink == "test-entity"

    # Check observations
    assert len(entity.observations) == 1
    obs = entity.observations[0]
    assert obs.content == "First observation"
    assert obs.category == ObservationCategory.NOTE  # Default category

    # Should start with no relations
    assert len(entity.relations) == 0


@pytest.mark.asyncio
async def test_create_entity_with_multiple_observations(client):
    """Test creating an entity with multiple observations."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                title="TestEntity",
                entity_type="test",
                observations=["First observation", "Second observation", "Third observation"],
            )
        ]
    )

    result = await create_entities(request)

    entity = result.entities[0]
    assert len(entity.observations) == 3

    # Each observation should have:
    # - content (the observation text)
    # - category (default NOTE)
    for obs in entity.observations:
        assert obs.content in ["First observation", "Second observation", "Third observation"]
        assert obs.category == ObservationCategory.NOTE


@pytest.mark.asyncio
async def test_create_multiple_entities(client):
    """Test creating multiple entities in one request."""
    request = CreateEntityRequest(
        entities=[
            Entity(title="Entity1", entity_type="test", observations=["Observation 1"]),
            Entity(title="Entity2", entity_type="test", observations=["Observation 2"]),
        ]
    )

    result = await create_entities(request)
    assert len(result.entities) == 2

    # Entities should be in order
    assert result.entities[0].title == "Entity1"
    assert result.entities[1].title == "Entity2"

    # Each should have its observation
    assert result.entities[0].observations[0].content == "Observation 1"
    assert result.entities[1].observations[0].content == "Observation 2"


@pytest.mark.asyncio
async def test_create_entity_without_observations(client):
    """Test creating an entity without any observations."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                title="TestEntity",
                entity_type="test",
            )
        ]
    )

    result = await create_entities(request)

    entity = result.entities[0]
    assert entity.title == "TestEntity"
    assert len(entity.observations) == 0


@pytest.mark.asyncio
async def test_create_minimal_entity(client):
    """Test creating an entity with just name and type."""
    request = CreateEntityRequest(entities=[Entity(title="MinimalEntity", entity_type="test")])

    result = await create_entities(request)

    entity = result.entities[0]
    assert entity.title == "MinimalEntity"
    assert entity.entity_type == "test"
    assert entity.permalink == "minimal-entity"
    assert entity.summary is None
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0
