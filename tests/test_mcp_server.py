"""Tests for the MCP server implementation."""
import pytest

from mcp.types import EmbeddedResource
from mcp.shared.exceptions import McpError
from basic_memory.mcp.server import MemoryServer, MIME_TYPE, BASIC_MEMORY_URI
from basic_memory.schemas import (
    CreateEntitiesResponse, SearchNodesResponse, AddObservationsResponse,
)

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def test_entity_data():
    """Sample data for creating a test entity using camelCase (like MCP will)."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entityType": "test",
            "description": "",  # Empty string instead of None
            "observations": [{"content": "This is a test observation"}]
        }]
    }

@pytest.fixture
def test_directory_entity_data():
    """Real data that caused failure in the tool."""
    return {
        "entities": [{
            "name": "Directory Organization", 
            "entityType": "memory", 
            "description": "Implemented filesystem organization by entity type", 
            "observations": [
                {"content": "Files are now organized by type using directories like entities/project/basic_memory"}, 
                {"content": "Entity IDs match filesystem paths for better mental model"}, 
                {"content": "Fixed path handling bugs by adding consistent get_entity_path helper"}
            ]
        }]
    }

@pytest.fixture
def test_entity_snake_case():
    """Same test data but using snake_case to test schema flexibility."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test",
            "description": "",  # Empty string instead of None
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
    search_schema = found_tools["search_nodes"].inputSchema
    assert "query" in search_schema["properties"]
    assert search_schema["required"] == ["query"]

@pytest.mark.anyio
async def test_create_directory_entity(test_directory_entity_data, memory_service, test_config):
    """Test creating entity with exactly the data that failed in the tool."""
    server_instance = MemoryServer(config=test_config)
    result = await server_instance.handle_call_tool(
        "create_entities", 
        test_directory_entity_data,
        memory_service=memory_service
    )
    
    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    
    # Verify entity creation
    response = CreateEntitiesResponse.model_validate_json(result[0].resource.text)
    assert len(response.entities) == 1
    assert response.entities[0].name == "Directory Organization"
    assert response.entities[0].entity_type == "memory"
    assert len(response.entities[0].observations) == 3

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
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert isinstance(result[0].resource.uri, type(BASIC_MEMORY_URI))
    assert str(result[0].resource.uri) == str(BASIC_MEMORY_URI)
    assert result[0].resource.mimeType == MIME_TYPE
    
    response = CreateEntitiesResponse.model_validate_json(result[0].resource.text)
    assert len(response.entities) == 1
    assert response.entities[0].name == "Test Entity"
    assert response.entities[0].entity_type == "test"
    assert len(response.entities[0].observations) == 1

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
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert isinstance(result[0].resource.uri, type(BASIC_MEMORY_URI))
    assert str(result[0].resource.uri) == str(BASIC_MEMORY_URI)
    assert result[0].resource.mimeType == MIME_TYPE
    
    response = CreateEntitiesResponse.model_validate_json(result[0].resource.text)
    assert len(response.entities) == 1
    assert response.entities[0].name == "Test Entity"
    assert response.entities[0].entity_type == "test"
    assert len(response.entities[0].observations) == 1

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
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert isinstance(result[0].resource.uri, type(BASIC_MEMORY_URI))
    assert str(result[0].resource.uri) == str(BASIC_MEMORY_URI)
    assert result[0].resource.mimeType == MIME_TYPE
    
    response = SearchNodesResponse.model_validate_json(result[0].resource.text)
    assert len(response.matches) == 1
    assert response.matches[0].name == "Test Entity"
    assert response.query == "Test Entity"

@pytest.mark.anyio
async def test_add_observations(test_entity_data, memory_service, test_config):
    """Test adding observations to an existing entity."""
    server_instance = MemoryServer(config=test_config)
    
    # First create an entity and get its ID from response
    create_result = await server_instance.handle_call_tool(
        "create_entities", 
        test_entity_data,
        memory_service=memory_service
    )
    
    create_response = CreateEntitiesResponse.model_validate_json(create_result[0].resource.text)
    entity_id = create_response.entities[0].id
    
    # Add new observations using camelCase
    result = await server_instance.handle_call_tool(
        "add_observations",
        {
            "entityId": entity_id,
            "observations": [{"content": "A new observation"}]
        },
        memory_service=memory_service
    )
    
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert isinstance(result[0].resource.uri, type(BASIC_MEMORY_URI))
    assert str(result[0].resource.uri) == str(BASIC_MEMORY_URI)
    assert result[0].resource.mimeType == MIME_TYPE
    
    response = AddObservationsResponse.model_validate_json(result[0].resource.text)
    assert response.entity_id == entity_id
    assert len(response.added_observations) == 1
    assert response.added_observations[0].content == "A new observation"

@pytest.mark.anyio
async def test_invalid_tool_name(test_config):
    """Test calling a non-existent tool."""
    server_instance = MemoryServer(config=test_config)
    with pytest.raises(McpError) as exc:
        await server_instance.handle_call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)

@pytest.mark.anyio
class TestInputValidation:
    """Test input validation for various tools."""
    
    async def test_missing_required_field(self, test_config):
        """Test validation when required fields are missing."""
        server_instance = MemoryServer(config=test_config)
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("search_nodes", {})
        assert "query" in str(exc.value).lower()
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("create_entities", {})
        assert "entities" in str(exc.value).lower()
    
    async def test_empty_arrays(self, test_config):
        """Test validation of array fields that can't be empty."""
        server_instance = MemoryServer(config=test_config)
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("create_entities", {"entities": []})
        assert "validation error" in str(exc.value).lower()
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("open_nodes", {"names": []})
        assert "validation error" in str(exc.value).lower()
    
    async def test_invalid_field_types(self, test_config):
        """Test validation when fields have wrong types."""
        server_instance = MemoryServer(config=test_config)
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("search_nodes", {"query": 123})
        assert "str" in str(exc.value).lower()
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("create_entities", {"entities": "not an array"})
        assert "array" in str(exc.value).lower() or "list" in str(exc.value).lower()
    
    async def test_invalid_nested_fields(self, test_config):
        """Test validation of nested object fields."""
        server_instance = MemoryServer(config=test_config)
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("create_entities", {
                "entities": [{
                    "name": "Test",
                    # Missing required entityType
                    "observations": []
                }]
            })
        assert "entitytype" in str(exc.value).lower()
        
        with pytest.raises(McpError) as exc:
            await server_instance.handle_call_tool("add_observations", {
                "entityId": "123",
                "observations": [{
                    # Missing required content field
                    "context": "test"
                }]
            })
        assert "content" in str(exc.value).lower()