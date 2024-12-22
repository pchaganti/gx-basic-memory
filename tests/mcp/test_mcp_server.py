"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS

from basic_memory.mcp.server import handle_call_tool


@pytest.mark.asyncio
async def test_invalid_tool_name(app):
    """Test calling a non-existent tool."""
    with pytest.raises(McpError) as exc:
        await handle_call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)


@pytest.mark.asyncio
async def test_missing_required_field(app):
    """Test validation when required fields are missing."""
    with pytest.raises(McpError) as exc:
        await handle_call_tool("search_nodes", {})
    assert "query" in str(exc.value).lower()

    with pytest.raises(McpError) as exc:
        await handle_call_tool("create_entities", {})
    assert "entities" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_empty_arrays(app):
    """Test validation of array fields that can't be empty."""
    with pytest.raises(McpError) as exc:
        await handle_call_tool("create_entities", {"entities": []})
    assert INVALID_PARAMS == exc.value.args[0]

    with pytest.raises(McpError) as exc:
        await handle_call_tool("open_nodes", {"entity_ids": []})
    assert INVALID_PARAMS == exc.value.args[0]


@pytest.mark.asyncio
async def test_invalid_field_types(app):
    """Test validation when fields have wrong types."""
    with pytest.raises(McpError) as exc:
        await handle_call_tool("search_nodes", {"query": 123})
    assert "str" in str(exc.value).lower()

    with pytest.raises(McpError) as exc:
        await handle_call_tool("create_entities", {"entities": "not an array"})
    assert "array" in str(exc.value).lower() or "list" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_invalid_nested_fields(app):
    """Test validation of nested object fields."""
    with pytest.raises(McpError) as exc:
        await handle_call_tool(
            "create_entities",
            {
                "entities": [
                    {
                        "name": "Test",
                        # Missing required entity_type
                        "observations": [],
                    }
                ]
            },
        )
    assert "entity_type" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_invalid_relation_format_to_id(app):
    """Test validation of relation data."""
    with pytest.raises(McpError) as exc:
        await handle_call_tool(
            "create_relations",
            {
                "relations": [
                    {
                        "from_id": 1,
                        # Missing to_id
                        "relation_type": "relates_to",
                    }
                ]
            },
        )
    assert "to_id" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_invalid_relation_format_relation_type(app):
    # Invalid relation type
    with pytest.raises(McpError) as exc:
        await handle_call_tool(
            "create_relations",
            {
                "relations": [
                    {
                        "from_id": 1,
                        "to_id": 2,
                        "relation_type": "",  # Empty relation type
                    }
                ]
            },
        )
    assert "relation_type" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_observation_validation_len(app):
    """Test validation specific to observations."""
    # Empty observations
    with pytest.raises(McpError) as exc:
        await handle_call_tool(
            "add_observations",
            {
                "entity_id": 1,
                "observations": ["", ""],  # Empty observations
            },
        )
    assert "observations" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_observation_validation_delete(app):
    # Empty deletions
    with pytest.raises(McpError) as exc:
        await handle_call_tool(
            "delete_observations",
            {
                "entity_id": 1,
                "deletions": [],  # Empty deletions
            },
        )
    assert INVALID_PARAMS == exc.value.args[0]


@pytest.mark.asyncio
async def test_edge_case_validation_search_len(app):
    """Test edge cases in validation."""
    # Very long strings
    with pytest.raises(McpError) as exc:
        await handle_call_tool(
            "search_nodes",
            {"query": "x" * 10000},  # Extremely long query
        )
