"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest
from mcp.types import EmbeddedResource

from basic_memory.schemas import CreateEntityResponse, AddObservationsResponse


@pytest.mark.asyncio
async def test_add_observations(test_entity_data, client, server):
    """Test adding observations to an existing entity."""

    # First create an entity
    create_result = await server.handle_call_tool("create_entities", test_entity_data)
    create_response = CreateEntityResponse.model_validate_json(create_result[0].resource.text)
    entity_id = create_response.entities[0].id

    # Add new observation
    result = await server.handle_call_tool(
        "add_observations", {"entity_id": entity_id, "observations": ["A new observation"]}
    )

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"

    # Verify observation was added
    response = AddObservationsResponse.model_validate_json(result[0].resource.text)
    assert response.entity_id == entity_id
    assert len(response.observations) == 1
    assert response.observations[0].content == "A new observation"

    # Verify through API
    api_response = await client.get(f"/knowledge/entities/{entity_id}")
    assert api_response.status_code == 200
    entity = api_response.json()
    assert len(entity["observations"]) == 2  # Original + new
    assert "A new observation" in [o["content"] for o in entity["observations"]]
