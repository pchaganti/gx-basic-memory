"""Tests for create_entities MCP tool."""

import pytest

from basic_memory.mcp.tools.knowledge import create_entities
from basic_memory.schemas.base import ObservationCategory, Entity, EntityType
from basic_memory.schemas.request import CreateEntityRequest


@pytest.mark.asyncio
async def test_create_basic_entity(client):
    """Test creating a simple entity."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="TestEntity",
                entity_type=EntityType.KNOWLEDGE,
                description="A test entity",
                observations=["First observation"]
            )
        ]
    )

    result = await create_entities(request)

    # Result should be an EntityListResponse
    assert len(result.entities) == 1
    
    # Check the created entity
    entity = result.entities[0]
    assert entity.name == "TestEntity"
    assert entity.entity_type == EntityType.KNOWLEDGE
    assert entity.path_id == "test_entity"
    assert entity.description == "A test entity"

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
                name="TestEntity",
                entity_type=EntityType.KNOWLEDGE,
                description="A test entity",
                observations=[
                    "First observation",
                    "Second observation",
                    "Third observation"
                ]
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
        assert obs.content in [
            "First observation",
            "Second observation", 
            "Third observation"
        ]
        assert obs.category == ObservationCategory.NOTE


@pytest.mark.asyncio
async def test_create_multiple_entities(client):
    """Test creating multiple entities in one request."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="Entity1",
                entity_type=EntityType.KNOWLEDGE,
                observations=["Observation 1"]
            ),
            Entity(
                name="Entity2", 
                entity_type=EntityType.KNOWLEDGE,
                observations=["Observation 2"]
            )
        ]
    )

    result = await create_entities(request)
    assert len(result.entities) == 2
    
    # Entities should be in order
    assert result.entities[0].name == "Entity1"
    assert result.entities[1].name == "Entity2"
    
    # Each should have its observation
    assert result.entities[0].observations[0].content == "Observation 1"
    assert result.entities[1].observations[0].content == "Observation 2"


@pytest.mark.asyncio
async def test_create_entity_without_observations(client):
    """Test creating an entity without any observations."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="TestEntity",
                entity_type=EntityType.KNOWLEDGE,
                description="A test entity without observations"
            )
        ]
    )

    result = await create_entities(request)

    entity = result.entities[0]
    assert entity.name == "TestEntity"
    assert len(entity.observations) == 0


@pytest.mark.asyncio
async def test_create_minimal_entity(client):
    """Test creating an entity with just name and type."""
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="MinimalEntity",
                entity_type=EntityType.KNOWLEDGE
            )
        ]
    )

    result = await create_entities(request)

    entity = result.entities[0]
    assert entity.name == "MinimalEntity"
    assert entity.entity_type == EntityType.KNOWLEDGE
    assert entity.path_id == "minimal_entity"
    assert entity.description is None
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0