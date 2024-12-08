"""Tests for the MCP server implementation."""
import pytest

from mcp.types import TextContent
from basic_memory.mcp import server

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def test_entity_data():
    """Sample data for creating a test entity using camelCase (like MCP will)."""
    return {
        "entities": [{
            "name": "Test Entity CamelCase",
            "entityType": "test",
            "observations": [{"content": "This is a test observation"}]
        }]
    }

@pytest.fixture
def test_entity_snake_case():
    """Same test data but using snake_case to test schema flexibility."""
    return {
        "entities": [{
            "name": "Test Entity SnakeCase",
            "entity_type": "test",
            "observations": [{"content": "This is a test observation"}]
        }]
    }

@pytest.mark.anyio
async def test_list_tools():
    """Test that server exposes expected tools."""
    tools = await server.handle_list_tools()
    
    # Check each expected tool is present
    expected_tools = {
        "create_entities", "search_nodes", "open_nodes",
        "add_observations", "create_relations", 
        "delete_entities", "delete_observations"
    }
    
    found_tools = {t.name: t for t in tools}
    assert found_tools.keys() == expected_tools
    
    # Verify schemas include required fields
    assert "entities" in found_tools["create_entities"].inputSchema["required"]
    assert "query" in found_tools["search_nodes"].inputSchema["required"]

@pytest.mark.anyio
async def test_create_entities_camel_case(test_entity_data):
    """Test creating an entity with camelCase data (like from MCP)."""
    result = await server.handle_call_tool("create_entities", test_entity_data)
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_create_entities_snake_case(test_entity_snake_case):
    """Test creating an entity with snake_case data (like internal usage)."""
    result = await server.handle_call_tool("create_entities", test_entity_snake_case)
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_search_nodes(test_entity_data):
    """Test searching for an entity after creating it."""
    # First create an entity
    await server.handle_call_tool("create_entities", test_entity_data)
    
    # Then search for it
    result = await server.handle_call_tool("search_nodes", {"query": "Test Entity"})
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_add_observations(test_entity_data):
    """Test adding observations to an existing entity."""
    # First create an entity
    await server.handle_call_tool("create_entities", test_entity_data)
    
    # Add new observations using camelCase
    result = await server.handle_call_tool("add_observations", {
        "entityId": "Test Entity",
        "observations": [{"content": "A new observation"}]
    })
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_invalid_tool_name():
    """Test calling a non-existent tool."""
    with pytest.raises(Exception) as exc:
        await server.handle_call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)

@pytest.mark.anyio
async def test_invalid_parameters():
    """Test validation with invalid parameters."""
    # Test missing required field
    with pytest.raises(Exception) as exc:
        await server.handle_call_tool("search_nodes", {})
    assert "query" in str(exc.value).lower()
    
    # Test empty entities list
    with pytest.raises(Exception) as exc:
        await server.handle_call_tool("create_entities", {"entities": []})
    assert "length" in str(exc.value).lower()

    # Test invalid case mixing (should pass due to aliases)
    result = await server.handle_call_tool("create_entities", {
        "entities": [{
            "name": "Mixed Case Test",
            "entityType": "test",  # camelCase
            "observations": [{"content": "Testing mixed case"}]
        }]
    })
    assert len(result) == 1
    assert "Mixed Case Test" in result[0].text