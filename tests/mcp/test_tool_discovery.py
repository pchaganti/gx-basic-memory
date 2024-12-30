"""Tests for knowledge discovery MCP tools."""

import pytest

from basic_memory.mcp.tools.discovery import get_entity_types
from basic_memory.schemas import Entity, CreateEntityRequest
from basic_memory.mcp.tools.knowledge import create_entities


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
