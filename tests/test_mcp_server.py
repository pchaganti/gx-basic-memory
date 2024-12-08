"""Tests for the MCP server implementation."""
import pytest
from pathlib import Path

from mcp.types import Tool, TextContent
from basic_memory.mcp import server

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def test_entity_data():
    return {
        "entities": [{
            "name": "Test Entity",
            "entityType": "test",
            "observations": ["This is a test observation"]
        }]
    }

@pytest.mark.anyio
async def test_list_tools():
    """Test that server exposes expected tools."""
    tools = server.list_tools()
    
    assert len(tools) == 2  # We have create_entities and search_nodes for now
    
    # Verify create_entities tool
    create_tool = next(t for t in tools if t.name == "create_entities")
    assert create_tool.inputSchema["required"] == ["entities"]
    assert "entities" in create_tool.inputSchema["properties"]
    
    # Verify search_nodes tool
    search_tool = next(t for t in tools if t.name == "search_nodes")
    assert search_tool.inputSchema["required"] == ["query"]
    assert "query" in search_tool.inputSchema["properties"]

@pytest.mark.anyio
async def test_call_create_entities(test_entity_data):
    """Test creating an entity through the tool interface."""
    result = await server.call_tool("create_entities", test_entity_data)
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    text_content = result[0].text
    assert "Test Entity" in text_content

@pytest.mark.anyio
async def test_call_search_nodes(test_entity_data):
    """Test searching for an entity after creating it."""
    # First create an entity
    await server.call_tool("create_entities", test_entity_data)
    
    # Then search for it
    result = await server.call_tool("search_nodes", {"query": "Test Entity"})
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_invalid_tool_name():
    """Test calling a non-existent tool."""
    with pytest.raises(Exception) as exc:  # We could be more specific about error type
        await server.call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)

@pytest.mark.anyio
async def test_invalid_parameters():
    """Test calling tools with invalid parameters."""
    # Test missing required parameter
    with pytest.raises(Exception) as exc:
        await server.call_tool("search_nodes", {})
    assert "query" in str(exc.value)
    
    # Test empty entities list
    with pytest.raises(Exception) as exc:
        await server.call_tool("create_entities", {"entities": []})
    assert "min_items" in str(exc.value)