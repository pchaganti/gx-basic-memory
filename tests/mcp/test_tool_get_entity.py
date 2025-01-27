"""Tests for get_entity MCP tool."""

import pytest
from mcp.server.fastmcp.exceptions import ToolError

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
                content="- [note] First observation",
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
    assert entity.permalink == "test-entity"

    # Check observations
    assert len(entity.observations) == 1
    obs = entity.observations[0]
    assert obs.content == "First observation"
    assert obs.category == ObservationCategory.NOTE




@pytest.mark.asyncio
async def test_get_nonexistent_entity(client):
    """Test attempting to get a non-existent entity."""
    with pytest.raises(ToolError):
        await get_entity("test/nonexistent")
