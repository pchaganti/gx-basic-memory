"""Tests for the MCP server implementation using FastAPI TestClient."""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from mcp.types import EmbeddedResource, INVALID_PARAMS
from mcp.shared.exceptions import McpError
from basic_memory.mcp.server import MemoryServer, MIME_TYPE, BASIC_MEMORY_URI
from basic_memory.api.app import app as fastapi_app
from basic_memory.deps import get_project_config, get_engine
from basic_memory.schemas import CreateEntityResponse, SearchNodesResponse, AddObservationsResponse


@pytest_asyncio.fixture
def app(test_config, engine) -> FastAPI:
    """Create test FastAPI application."""
    app = fastapi_app
    app.dependency_overrides[get_project_config] = lambda: test_config
    app.dependency_overrides[get_engine] = lambda: engine
    return app

@pytest_asyncio.fixture()
async def server(app) -> MemoryServer:
    server = MemoryServer()
    await server.setup()
    return server

@pytest_asyncio.fixture
async def client(app: FastAPI):
    """Create test client that both MCP and tests will use."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
def test_entity_data():
    """Sample data for creating a test entity."""
    return {
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test",
            "description": "",  # Empty string instead of None
            "observations": ["This is a test observation"]
        }]
    }


@pytest_asyncio.fixture
def test_directory_entity_data():
    """Real data that caused failure in the tool."""
    return {
        "entities": [{
            "name": "Directory Organization",
            "entity_type": "memory",
            "description": "Implemented filesystem organization by entity type",
            "observations": [
                "Files are now organized by type using directories like entities/project/basic_memory",
                "Entity IDs match filesystem paths for better mental model",
                "Fixed path handling bugs by adding consistent get_entity_path helper"
            ]
        }]
    }


@pytest.mark.asyncio
async def test_list_tools(server):
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
    search_schema = found_tools["search_nodes"].inputSchema
    assert "query" in search_schema["properties"]
    assert search_schema["required"] == ["query"]


@pytest.mark.asyncio
async def test_create_directory_entity(test_directory_entity_data, client, server):
    """Test creating entity with exactly the data that failed in the tool."""
    result = await server.handle_call_tool(
        "create_entities",
        test_directory_entity_data
    )

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"

    # Verify entity creation
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
    assert len(response.entities) == 1
    created = response.entities[0]
    assert created.name == "Directory Organization"
    assert created.entity_type == "memory"
    assert len(created.observations) == 3

    # Verify entity exists through API
    api_response = await client.get(f"/knowledge/entities/{created.id}")
    assert api_response.status_code == 200
    entity = api_response.json()
    assert entity["name"] == "Directory Organization"


@pytest.mark.asyncio
async def test_search_nodes(test_entity_data, client, server):
    """Test searching for an entity after creating it."""

    # First create an entity
    await server.handle_call_tool("create_entities", test_entity_data)

    # Then search for it
    result = await server.handle_call_tool(
        "search_nodes",
        {"query": "Test Entity"}
    )

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert isinstance(result[0].resource.uri, type(BASIC_MEMORY_URI))
    assert str(result[0].resource.uri) == str(BASIC_MEMORY_URI)
    assert result[0].resource.mimeType == MIME_TYPE

    # Verify search results
    response = SearchNodesResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
    assert len(response.matches) == 1
    assert response.matches[0].name == "Test Entity"
    assert response.query == "Test Entity"

    # Verify through API
    api_response = await client.post("/knowledge/search", json={"query": "Test Entity"})
    assert api_response.status_code == 200
    data = api_response.json()
    assert len(data["matches"]) == 1
    assert data["matches"][0]["name"] == "Test Entity"


@pytest.mark.asyncio
async def test_add_observations(test_entity_data, client, server):
    """Test adding observations to an existing entity."""

    # First create an entity
    create_result = await server.handle_call_tool("create_entities", test_entity_data)
    create_response = CreateEntityResponse.model_validate_json(create_result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
    entity_id = create_response.entities[0].id

    # Add new observation
    result = await server.handle_call_tool(
        "add_observations",
        {
            "entity_id": entity_id,
            "observations": ["A new observation"]
        }
    )

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"

    # Verify observation was added
    response = AddObservationsResponse.model_validate_json(result[0].resource.text)
    assert response.entity_id == entity_id
    assert len(response.observations) == 1
    assert response.observations[0].content == "A new observation"

    # Verify through API
    api_response = await client.get(f"/knowledge/entities/{entity_id}")
    assert api_response.status_code == 200
    entity = api_response.json()
    assert len(entity["observations"]) == 2  # Original + new
    assert "A new observation" in [o["content"] for o in entity["observations"]]


@pytest.mark.asyncio
async def test_invalid_tool_name(server):
    """Test calling a non-existent tool."""
    with pytest.raises(McpError) as exc:
        await server.handle_call_tool("not_a_tool", {})
    assert "Unknown tool" in str(exc.value)


@pytest.mark.asyncio
class TestInputValidation:
    """Test input validation for various tools."""

    async def test_missing_required_field(self, server):
        """Test validation when required fields are missing."""

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("search_nodes", {})
        assert "query" in str(exc.value).lower()

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("create_entities", {})
        assert "entities" in str(exc.value).lower()

    async def test_empty_arrays(self, server):
        """Test validation of array fields that can't be empty."""

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("create_entities", {"entities": []})
        assert INVALID_PARAMS == exc.value.args[0]

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("open_nodes", {"names": []})
        assert INVALID_PARAMS == exc.value.args[0]

    async def test_invalid_field_types(self, server):
        """Test validation when fields have wrong types."""

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("search_nodes", {"query": 123})
        assert "str" in str(exc.value).lower()

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("create_entities", {"entities": "not an array"})
        assert "array" in str(exc.value).lower() or "list" in str(exc.value).lower()

    async def test_invalid_nested_fields(self, server):
        """Test validation of nested object fields."""

        with pytest.raises(McpError) as exc:
            await server.handle_call_tool("create_entities", {
                "entities": [{
                    "name": "Test",
                    # Missing required entity_type
                    "observations": []
                }]
            })
        assert "entity_type" in str(exc.value).lower()