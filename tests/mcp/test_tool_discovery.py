"""Tests for knowledge discovery MCP tools."""

import pytest

from basic_memory.mcp.tools.discovery import (
    get_observation_categories,
)
from basic_memory.schemas import Entity, CreateEntityRequest, ObservationCategoryList, EntityType
from basic_memory.mcp.tools.knowledge import create_entities, add_observations
from basic_memory.schemas.request import ObservationCreate, AddObservationsRequest


@pytest.mark.asyncio
async def test_get_observation_categories(client):
    """Test getting list of observation categories."""
    # First create an entity with categorized observations
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="Test Entity",
                entity_type=EntityType.KNOWLEDGE,
                description="Test entity",
                observations=[],
            )
        ]
    )
    entity = (await create_entities(request)).entities[0]

    # Add observations with different categories
    observations = [
        ObservationCreate(content="Technical detail", category="tech"),
        ObservationCreate(content="Design decision", category="design"),
        ObservationCreate(content="Feature spec", category="feature"),
        ObservationCreate(content="General note", category="note"),
    ]

    await add_observations(
        AddObservationsRequest(path_id=entity.path_id, observations=observations)
    )

    # Get categories
    result = await get_observation_categories()
    observation_categories = ObservationCategoryList.model_validate(result)

    # Verify results
    assert "tech" in observation_categories.categories
    assert "design" in observation_categories.categories
    assert "feature" in observation_categories.categories
    assert "note" in observation_categories.categories


@pytest.mark.asyncio
async def test_get_observation_categories_empty(client):
    """Test getting observation categories when no observations exist."""
    result = await get_observation_categories()
    observation_categories = ObservationCategoryList.model_validate(result)

    # Should return empty list, not error
    observation_categories.categories == []
