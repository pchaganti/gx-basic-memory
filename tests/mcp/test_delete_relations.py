"""Tests for MCP delete_relations tool."""

import pytest

from basic_memory.mcp.server import handle_call_tool
from basic_memory.schemas import SearchNodesResponse


@pytest.mark.asyncio
async def test_delete_relations(app):
    """Test deleting relations between entities."""
    # Create test entities with relation
    entities = {
        "entities": [
            {"name": "RelSource", "entity_type": "test", "observations": ["Source entity"]},
            {"name": "RelTarget", "entity_type": "test", "observations": ["Target entity"]},
        ]
    }
    await handle_call_tool("create_entities", entities)

    # Create relation
    relation = {
        "relations": [
            {
                "from_id": "test/relsource",
                "to_id": "test/reltarget",
                "relation_type": "relates_to",
            }
        ]
    }
    await handle_call_tool("create_relations", relation)

    # Delete the relation
    await handle_call_tool(
        "delete_relations",
        {
            "relations": [
                {
                    "from_id": "test/relsource",
                    "to_id": "test/reltarget",
                    "relation_type": "relates_to",
                }
            ]
        },
    )

    # Verify through search
    search_result = await handle_call_tool("search_nodes", {"query": "relsource"})
    search_response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]

    # Source entity should exist but have no relations
    assert len(search_response.matches) == 1
    assert len(search_response.matches[0].relations) == 0
