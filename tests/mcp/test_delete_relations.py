"""Tests for MCP delete_relations tool."""

import pytest

from basic_memory.mcp.server import handle_call_tool
from basic_memory.schemas import SearchNodesResponse, CreateEntityResponse


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
    create_entity_result = await handle_call_tool("create_entities", entities)
    create_entity_response = CreateEntityResponse.model_validate_json(
        create_entity_result[0].resource.text  # pyright: ignore [reportAttributeAccessIssue]
    )
    from_entity = create_entity_response.entities[0]
    to_entity = create_entity_response.entities[1]

    # Create relation
    relation = {
        "relations": [
            {
                "from_id": from_entity.id,
                "to_id": to_entity.id,
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
                    "from_id": from_entity.id,
                    "to_id": to_entity.id,
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
