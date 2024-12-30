"""Tests for knowledge discovery MCP tools."""

import pytest

from basic_memory.mcp.tools.discovery import get_entity_types, get_observation_categories
from basic_memory.schemas import Entity, CreateEntityRequest, AddObservationsRequest
from basic_memory.mcp.tools.knowledge import create_entities, add_observations
from basic_memory.schemas.request import ObservationCreate


@pytest.mark.asyncio
async def test_get_entity_types(client):
    """Test getting list of entity types."""
    # First create some test entities
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="Memory Service",
                entity_type="technical_component",
                path_id="component/memory_service",
                description="Core memory service",
                observations=["First observation"]
            ),
            Entity(
                name="File Format",
                entity_type="specification",
                path_id="specification/file_format",
                description="File format spec",
                observations=["Format details"]
            ),
            Entity(
                name="Tech Choice",
                entity_type="decision",
                path_id="decision/tech_choice",
                description="Technology decision",
                observations=["Decision context"]
            )
        ]
    )
    await create_entities(request)

    # Get entity types
    result = await get_entity_types()

    # Verify the result
    assert isinstance(result, list)
    assert all(isinstance(t, str) for t in result)
    assert "technical_component" in result
    assert "specification" in result
    assert "decision" in result

    # Should be unique
    assert len(result) == len(set(result))
    

@pytest.mark.asyncio
async def test_get_entity_types_empty(client):
    """Test getting entity types when no entities exist."""
    # Get types (should work with empty DB)
    result = await get_entity_types()
    
    # Should return empty list, not error
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_observation_categories(client):
    """Test getting list of observation categories."""
    # First create an entity with categorized observations
    request = CreateEntityRequest(
        entities=[
            Entity(
                name="Test Entity",
                entity_type="test",
                path_id="test/entity",
                description="Test entity",
                observations=[]
            )
        ]
    )
    entity = (await create_entities(request)).entities[0]
    
    # Add observations with different categories
    observations = [
        ObservationCreate(content="Technical detail", category="tech"),
        ObservationCreate(content="Design decision", category="design"),
        ObservationCreate(content="Feature spec", category="feature"),
        ObservationCreate(content="General note", category="note")
    ]
    
    await add_observations(AddObservationsRequest(path_id=entity.path_id, observations=observations))

    # Get categories
    result = await get_observation_categories()

    # Verify results
    assert isinstance(result, list)
    assert all(isinstance(c, str) for c in result)
    assert "tech" in result
    assert "design" in result
    assert "feature" in result
    assert "note" in result

    # Should be unique
    assert len(result) == len(set(result))


@pytest.mark.asyncio
async def test_get_observation_categories_empty(client):
    """Test getting observation categories when no observations exist."""
    result = await get_observation_categories()
    
    # Should return empty list, not error
    assert isinstance(result, list)
    assert len(result) == 0
