"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS

from basic_memory.schemas import CreateEntityResponse, SearchNodesResponse


@pytest.mark.asyncio
async def test_invalid_tool_name(server):
    """Test calling a non-existent tool."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)


@pytest.mark.asyncio
async def test_missing_required_field(server):
    """Test validation when required fields are missing."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("search_nodes", {})
    assert "query" in str(exc.value).lower()

    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("create_entities", {})
    assert "entities" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_empty_arrays(server):
    """Test validation of array fields that can't be empty."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("create_entities", {"entities": []})
    assert INVALID_PARAMS == exc.value.args[0]

    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("open_nodes", {"entity_ids": []})
    assert INVALID_PARAMS == exc.value.args[0]


@pytest.mark.asyncio
async def test_invalid_field_types(server):
    """Test validation when fields have wrong types."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("search_nodes", {"query": 123})
    assert "str" in str(exc.value).lower()

    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("create_entities", {"entities": "not an array"})
    assert "array" in str(exc.value).lower() or "list" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_invalid_nested_fields(server):
    """Test validation of nested object fields."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool(
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
async def test_invalid_relation_format_to_id(server):
    """Test validation of relation data."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool(
            "create_relations",
            {
                "relations": [
                    {
                        "from_id": "test/entity1",
                        # Missing to_id
                        "relation_type": "relates_to",
                    }
                ]
            },
        )
    assert "to_id" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_invalid_relation_format_relation_type(server):
    # Invalid relation type
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool(
            "create_relations",
            {
                "relations": [
                    {
                        "from_id": "test/entity1",
                        "to_id": "test/entity2",
                        "relation_type": "",  # Empty relation type
                    }
                ]
            },
        )
    assert "relation_type" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_observation_validation_len(server):
    """Test validation specific to observations."""
    # Empty observations
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool(
            "add_observations",
            {
                "entity_id": "test/entity1",
                "observations": ["", ""],  # Empty observations
            },
        )
    assert "observations" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_observation_validation_delete(server):
    # Empty deletions
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool(
            "delete_observations",
            {
                "entity_id": "test/entity1",
                "deletions": [],  # Empty deletions
            },
        )
    assert INVALID_PARAMS == exc.value.args[0]


@pytest.mark.asyncio
async def test_edge_case_validation_search_len(server):
    """Test edge cases in validation."""
    # Very long strings
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool(
            "search_nodes",
            {"query": "x" * 10000},  # Extremely long query
        )


@pytest.mark.asyncio
async def test_edge_case_validation_name_sanitization(server):
    """Test that entity names are properly sanitized for IDs."""
    # Test cases for different sanitization scenarios
    test_cases = [
        {
            "name": "🧪 FOO & File (1)",  # Emoji and special chars
            "expected_id": "test/foo_file_1",
        },
        {
            "name": "BARR    Multiple   Spaces",  # Multiple spaces
            "expected_id": "test/barr_multiple_spaces",
        },
        {
            "name": "LOTSOF@#$Special&*Chars",  # Special characters
            "expected_id": "test/lotsofspecialchars",
        },
        {
            "name": "\x00null",  # Null byte
            "expected_id": "test/null",
        },
        {
            "name": "\nline",  # Newline
            "expected_id": "test/line",
        },
    ]

    for test in test_cases:
        result = await server.handle_call_tool(
            "create_entities",
            {
                "entities": [
                    {
                        "name": test["name"],
                        "entity_type": "test",
                        "observations": [],
                    }
                ]
            },
        )

        response = CreateEntityResponse.model_validate_json(result[0].resource.text)
        entity = response.entities[0]

        # Original name should be preserved
        assert entity.name == test["name"]
        # ID should be sanitized
        assert entity.id == test["expected_id"]

        # Verify we can find it with original name
        search_result = await server.handle_call_tool("search_nodes", {"query": test["name"]})
        search_response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)
        assert len(search_response.matches) > 0
