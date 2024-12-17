"""Tests for MCP delete_observations tool."""

import pytest

from basic_memory.schemas import CreateEntityResponse, SearchNodesResponse


@pytest.mark.asyncio
async def test_delete_observations(server):
    """Test deleting specific observations from an entity."""
    # Create entity with multiple observations
    entity_data = {
        "entities": [{
            "name": "ObsDeleteTest",
            "entity_type": "test",
            "observations": [
                "Keep this observation",
                "Delete this observation",
                "Also keep this"
            ]
        }]
    }
    create_result = await server.handle_call_tool("create_entities", entity_data)
    create_response = CreateEntityResponse.model_validate_json(create_result[0].resource.text)
    entity_id = create_response.entities[0].id

    # Delete specific observation
    await server.handle_call_tool(
        "delete_observations",
        {
            "entity_id": entity_id,
            "deletions": ["Delete this observation"]
        }
    )

    # Verify through search
    search_result = await server.handle_call_tool(
        "search_nodes",
        {"query": "ObsDeleteTest"}
    )
    search_response = SearchNodesResponse.model_validate_json(
        search_result[0].resource.text
    )

    # Check remaining observations
    entity = search_response.matches[0]
    observations = [o.content for o in entity.observations]
    assert len(observations) == 2
    assert "Delete this observation" not in observations
    assert "Keep this observation" in observations
    assert "Also keep this" in observations