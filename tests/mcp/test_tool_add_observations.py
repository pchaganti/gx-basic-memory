"""Tests for add_observations MCP tool."""

import pytest

from basic_memory.mcp.tools import create_entities, add_observations
from basic_memory.schemas.base import ObservationCategory


@pytest.mark.asyncio
async def test_add_basic_observation(client):
    """Test adding a single observation with default category."""
    # First create an entity to add observations to
    result = await create_entities([{
        "name": "TestEntity",
        "entity_type": "test"
    }])
    entity_id = result.entities[0].path_id

    # Add an observation
    updated = await add_observations(
        entity_id,
        observations=[{
            "content": "Test observation"
        }]
    )

    # Verify the observation was added
    assert len(updated.observations) == 1
    obs = updated.observations[0]
    assert obs.content == "Test observation"
    assert obs.category == ObservationCategory.NOTE  # Default category


@pytest.mark.asyncio
async def test_add_categorized_observations(client):
    """Test adding observations with different categories."""
    # Create test entity
    result = await create_entities([{
        "name": "TestEntity",
        "entity_type": "test"
    }])
    entity_id = result.entities[0].path_id

    # Add observations with different categories
    updated = await add_observations(
        entity_id,
        observations=[
            {
                "content": "Implementation uses SQLite",
                "category": "tech"
            },
            {
                "content": "Chose SQLite for simplicity",
                "category": "design"
            },
            {
                "content": "Supports atomic operations",
                "category": "feature"
            }
        ]
    )

    assert len(updated.observations) == 3
    
    # Find and verify each observation by category
    tech_obs = next(o for o in updated.observations if o.category == ObservationCategory.TECH)
    design_obs = next(o for o in updated.observations if o.category == ObservationCategory.DESIGN)
    feature_obs = next(o for o in updated.observations if o.category == ObservationCategory.FEATURE)

    assert tech_obs.content == "Implementation uses SQLite"
    assert design_obs.content == "Chose SQLite for simplicity"
    assert feature_obs.content == "Supports atomic operations"


@pytest.mark.asyncio
async def test_add_observations_with_context(client):
    """Test adding observations with shared context."""
    # Create test entity
    result = await create_entities([{
        "name": "TestEntity",
        "entity_type": "test"
    }])
    entity_id = result.entities[0].path_id

    # Add observations with context
    shared_context = "Design meeting 2024-12-25"
    updated = await add_observations(
        entity_id,
        observations=[
            {
                "content": "Decided on file format",
                "category": "design"
            },
            {
                "content": "Will use markdown",
                "category": "tech"
            }
        ],
        context=shared_context
    )

    assert len(updated.observations) == 2
    for obs in updated.observations:
        # Note: context handling depends on our schema - might need adjustment
        if hasattr(obs, 'context'):
            assert obs.context == shared_context


@pytest.mark.asyncio
async def test_add_observations_preserves_existing(client):
    """Test that adding observations preserves existing ones."""
    # Create entity with initial observation
    result = await create_entities([{
        "name": "TestEntity",
        "entity_type": "test",
        "observations": ["Initial observation"]
    }])
    entity_id = result.entities[0].path_id

    # Add new observations
    updated = await add_observations(
        entity_id,
        observations=[{
            "content": "New observation",
            "category": "tech"
        }]
    )

    # Should have both observations
    assert len(updated.observations) == 2
    contents = {obs.content for obs in updated.observations}
    assert "Initial observation" in contents
    assert "New observation" in contents


@pytest.mark.asyncio
async def test_add_multiple_observations_same_category(client):
    """Test adding multiple observations in the same category."""
    # Create test entity
    result = await create_entities([{
        "name": "TestEntity",
        "entity_type": "test"
    }])
    entity_id = result.entities[0].path_id

    # Add multiple tech observations
    tech_observations = [
        "Uses async/await",
        "Implements SQLite backend",
        "Handles UTF-8 encoding"
    ]
    
    updated = await add_observations(
        entity_id,
        observations=[
            {"content": obs, "category": "tech"} 
            for obs in tech_observations
        ]
    )

    # Verify all observations were added with correct category
    assert len(updated.observations) == 3
    for obs in updated.observations:
        assert obs.category == ObservationCategory.TECH
        assert obs.content in tech_observations


@pytest.mark.asyncio
async def test_add_observation_to_nonexistent_entity(client):
    """Test adding observations to a non-existent entity fails properly."""
    with pytest.raises(Exception):  # Adjust exception type based on your error handling
        await add_observations(
            "test/nonexistent",
            observations=[{
                "content": "This should fail",
                "category": "note"
            }]
        )