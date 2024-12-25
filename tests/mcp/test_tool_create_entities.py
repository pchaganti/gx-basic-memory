"""Tests for create_entities MCP tool."""

import pytest

from basic_memory.mcp.tools import create_entities
from basic_memory.schemas.base import ObservationCategory


@pytest.mark.asyncio
async def test_create_basic_entity(client):
    """Test creating a simple entity."""
    result = await create_entities([
        {
            "name": "TestEntity",
            "entity_type": "test",
            "description": "A test entity",
            "observations": ["First observation"]
        }
    ])

    # Result should be an EntityListResponse
    assert len(result.entities) == 1
    
    # Check the created entity
    entity = result.entities[0]
    assert entity.name == "TestEntity"
    assert entity.entity_type == "test"
    assert entity.path_id == "test/test_entity"
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
    result = await create_entities([
        {
            "name": "TestEntity",
            "entity_type": "test",
            "description": "A test entity",
            "observations": [
                "First observation",
                "Second observation",
                "Third observation"
            ]
        }
    ])

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
    entities = [
        {
            "name": "Entity1",
            "entity_type": "test",
            "observations": ["Observation 1"]
        },
        {
            "name": "Entity2", 
            "entity_type": "test",
            "observations": ["Observation 2"]
        }
    ]

    result = await create_entities(entities)
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
    result = await create_entities([
        {
            "name": "TestEntity",
            "entity_type": "test",
            "description": "A test entity without observations"
        }
    ])

    entity = result.entities[0]
    assert entity.name == "TestEntity"
    assert len(entity.observations) == 0


@pytest.mark.asyncio
async def test_create_minimal_entity(client):
    """Test creating an entity with just name and type."""
    result = await create_entities([
        {
            "name": "MinimalEntity",
            "entity_type": "test"
        }
    ])

    entity = result.entities[0]
    assert entity.name == "MinimalEntity"
    assert entity.entity_type == "test"
    assert entity.path_id == "test/minimal_entity"
    assert entity.description is None
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0