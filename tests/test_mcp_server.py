"""Tests for the MCP server implementation."""
import pytest
import json
from pathlib import Path

from mcp.types import TextContent
from basic_memory.mcp.server import MemoryServer
from basic_memory.config import ProjectConfig

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def test_config():
    """Test configuration using in-memory DB."""
    return ProjectConfig(
        name="test",
        db_url="sqlite+aiosqlite:///:memory:",
        path=Path("/tmp/basic-memory-test")  # Will be created and validated
    )

@pytest.fixture
def test_entity_data():
    """Sample data for creating a test entity using camelCase (like MCP will)."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entityType": "test",
            "observations": [{"content": "This is a test observation"}]
        }]
    }

@pytest.fixture
def test_entity_snake_case():
    """Same test data but using snake_case to test schema flexibility."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test",
            "observations": [{"content": "This is a test observation"}]
        }]
    }

@pytest.mark.anyio
async def test_list_tools(test_config):
    """Test that server exposes expected tools."""
    server_instance = MemoryServer(config=test_config)
    tools = await server_instance.handle_list_tools()
    
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
async def test_create_entities_camel_case(test_entity_data, memory_service, test_config):
    """Test creating an entity with camelCase data (like from MCP)."""
    server_instance = MemoryServer(config=test_config)
    result = await server_instance.handle_call_tool(
        "create_entities", 
        test_entity_data,
        memory_service=memory_service
    )
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_create_entities_snake_case(test_entity_snake_case, memory_service, test_config):
    """Test creating an entity with snake_case data (like internal usage)."""
    server_instance = MemoryServer(config=test_config)
    result = await server_instance.handle_call_tool(
        "create_entities", 
        test_entity_snake_case,
        memory_service=memory_service
    )
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_search_nodes(test_entity_data, memory_service, test_config):
    """Test searching for an entity after creating it."""
    server_instance = MemoryServer(config=test_config)
    
    # First create an entity
    await server_instance.handle_call_tool(
        "create_entities", 
        test_entity_data,
        memory_service=memory_service
    )
    
    # Then search for it
    result = await server_instance.handle_call_tool(
        "search_nodes", 
        {"query": "Test Entity"},
        memory_service=memory_service
    )
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Test Entity" in result[0].text

@pytest.mark.anyio
async def test_add_observations(test_entity_data, memory_service, test_config):
    """Test adding observations to an existing entity."""
    server_instance = MemoryServer(config=test_config)
    
    # First create an entity and get its ID
    create_result = await server_instance.handle_call_tool(
        "create_entities", 
        test_entity_data,
        memory_service=memory_service
    )
    # Extract ID from response
    created_entity = json.loads(create_result[0].text.replace("'", '"'))[0]
    entity_id = created_entity["id"]
    
    # Add new observations using camelCase
    result = await server_instance.handle_call_tool(
        "add_observations",
        {
            "entityId": entity_id,  # Use ID instead of name
            "observations": [{"content": "A new observation"}]
        },
        memory_service=memory_service
    )
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert entity_id in result[0].text

@pytest.mark.anyio
async def test_invalid_tool_name(test_config):
    """Test calling a non-existent tool."""
    server_instance = MemoryServer(config=test_config)
    with pytest.raises(Exception) as exc:
        await server_instance.handle_call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)

@pytest.mark.anyio
async def test_invalid_parameters(test_config):
    """Test validation with invalid parameters."""
    server_instance = MemoryServer(config=test_config)
    
    # Test missing required field
    with pytest.raises(Exception) as exc:
        await server_instance.handle_call_tool("search_nodes", {})
    assert "query" in str(exc.value).lower()
    
    # Test empty entities list
    with pytest.raises(Exception) as exc:
        await server_instance.handle_call_tool("create_entities", {"entities": []})
    assert "min_items" in str(exc.value).lower()
    
    # Test invalid case mixing (should still work with aliases)
    result = await server_instance.handle_call_tool(
        "create_entities",
        {
            "entities": [{
                "name": "Mixed Case Test",
                "entityType": "test",  # camelCase
                "observations": [{"content": "Testing case handling"}]
            }]
        }
    )
    assert len(result) == 1
    assert "Mixed Case Test" in result[0].text