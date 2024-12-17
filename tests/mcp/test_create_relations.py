"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest

from basic_memory.schemas import SearchNodesResponse
from basic_memory.utils import sanitize_name


@pytest.mark.asyncio
async def test_create_relations(test_entity_data, client, server):
    """Test creating relations between entities."""
    # Create two test entities
    entity_data = {
        "entities": [
            {"name": "TestEntityA", "entity_type": "test", "observations": ["Entity A"]},
            {"name": "TestEntityB", "entity_type": "test", "observations": ["Entity B"]},
        ]
    }

    await server.handle_call_tool("create_entities", entity_data)

    # Create relation between them
    relation_data = {
        "relations": [
            {
                "from_id": "test/TestEntityA",
                "to_id": "test/TestEntityB",
                "relation_type": "relates_to",
            }
        ]
    }

    result = await server.handle_call_tool("create_relations", relation_data)

    # Verify through search
    search_result = await server.handle_call_tool("search_nodes", {"query": "TestEntityA"})
    response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)

    assert len(response.matches) == 1
    entity = response.matches[0]
    assert len(entity.relations) == 1
    assert entity.relations[0].to_id == sanitize_name("test/TestEntityB")
    assert entity.relations[0].relation_type == "relates_to"
