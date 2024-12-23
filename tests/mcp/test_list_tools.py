"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest

from basic_memory.mcp.server import handle_list_tools


@pytest.mark.asyncio
async def test_list_tools(app):
    """Test that server exposes expected tools."""

    tools = await handle_list_tools()

    # Check each expected tool is present
    expected_tools = {
        # Knowledge graph tools
        "create_entities",
        "search_nodes",
        "open_nodes",
        "add_observations",
        "create_relations",
        "delete_entities",
        "delete_observations",
        "delete_relations",
        # Document tools
        "create_document",
        "list_documents",
        "get_document",
        "update_document",
        "delete_document",
    }

    found_tools = {t.name: t for t in tools}
    assert found_tools.keys() == expected_tools

    # Verify schemas include required fields
    search_schema = found_tools["search_nodes"].inputSchema
    assert "query" in search_schema["properties"]
    assert search_schema["required"] == ["query"]

    # Verify document tool schemas
    create_doc_schema = found_tools["create_document"].inputSchema
    assert "path" in create_doc_schema["properties"]
    assert "content" in create_doc_schema["properties"]
    assert set(create_doc_schema["required"]) == {"path", "content"}

    get_doc_schema = found_tools["get_document"].inputSchema
    assert "id" in get_doc_schema["properties"]
    assert get_doc_schema["required"] == ["id"]