"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from mcp.shared.exceptions import McpError
from mcp.types import EmbeddedResource, INVALID_PARAMS

from basic_memory.api.app import app as fastapi_app
from basic_memory.deps import get_project_config, get_engine_factory
from basic_memory.mcp.server import MemoryServer, MIME_TYPE, BASIC_MEMORY_URI
from basic_memory.schemas import CreateEntityResponse, SearchNodesResponse, AddObservationsResponse
from basic_memory.utils import normalize_entity_id


@pytest_asyncio.fixture
def app(test_config, engine_session_factory) -> FastAPI:
    """Create test FastAPI application."""
    app = fastapi_app
    app.dependency_overrides[get_project_config] = lambda: test_config
    app.dependency_overrides[get_engine_factory] = lambda: engine_session_factory
    return app


@pytest_asyncio.fixture()
async def server(app) -> MemoryServer:
    server = MemoryServer()
    await server.setup()
    return server


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """Create test client that both MCP and tests will use."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
def test_entity_data():
    """Sample data for creating a test entity."""
    return {
        "entities": [
            {
                "name": "Test Entity",
                "entity_type": "test",
                "description": "",  # Empty string instead of None
                "observations": ["This is a test observation"],
            }
        ]
    }


@pytest_asyncio.fixture
def test_directory_entity_data():
    """Real data that caused failure in the tool."""
    return {
        "entities": [
            {
                "name": "Directory Organization",
                "entity_type": "memory",
                "description": "Implemented filesystem organization by entity type",
                "observations": [
                    "Files are now organized by type using directories like entities/project/basic_memory",
                    "Entity IDs match filesystem paths for better mental model",
                    "Fixed path handling bugs by adding consistent get_entity_path helper",
                ],
            }
        ]
    }


@pytest.mark.asyncio
async def test_create_single_entity(server):
    """Test creating a single entity."""
    entity_data = {
        "entities": [
            {"name": "SingleTest", "entity_type": "test", "observations": ["Test observation"]}
        ]
    }

    result = await server.handle_call_tool("create_entities", entity_data)

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert result[0].resource.mimeType == MIME_TYPE

    # Verify entity creation
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)
    assert len(response.entities) == 1
    entity = response.entities[0]
    assert entity.name == "SingleTest"
    assert entity.entity_type == "test"
    assert len(entity.observations) == 1
    assert entity.observations[0].content == "Test observation"
    assert entity.id == "test/singletest"

    # Verify entity can be found via search
    search_result = await server.handle_call_tool("search_nodes", {"query": "SingleTest"})
    search_response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)
    assert len(search_response.matches) == 1
    assert search_response.matches[0].name == "SingleTest"


@pytest.mark.asyncio
async def test_create_multiple_entities(server):
    """Test creating multiple entities in one call."""
    entity_data = {
        "entities": [
            {"name": "BulkTest1", "entity_type": "test", "observations": ["First bulk test"]},
            {"name": "BulkTest2", "entity_type": "test", "observations": ["Second bulk test"]},
            {"name": "BulkTest3", "entity_type": "demo", "observations": ["Third bulk test"]},
        ]
    }

    result = await server.handle_call_tool("create_entities", entity_data)

    # Verify response
    assert len(result) == 1
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)

    # Verify all entities were created
    assert len(response.entities) == 3

    # Check specific entities
    entities = {e.name: e for e in response.entities}
    assert "BulkTest1" in entities
    assert "BulkTest2" in entities
    assert "BulkTest3" in entities

    # Verify IDs were generated correctly
    assert entities["BulkTest1"].id == "test/bulktest1"
    assert entities["BulkTest2"].id == "test/bulktest2"
    assert entities["BulkTest3"].id == "demo/bulktest3"

    # Verify observations were saved
    assert len(entities["BulkTest1"].observations) == 1
    assert entities["BulkTest1"].observations[0].content == "First bulk test"

    # Verify entities can be found via search
    search_result = await server.handle_call_tool("search_nodes", {"query": "BulkTest"})
    search_response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)
    assert len(search_response.matches) == 3


@pytest.mark.asyncio
async def test_create_entity_with_all_fields(server):
    """Test creating entity with all possible fields populated."""
    entity_data = {
        "entities": [
            {
                "name": "FullEntity",
                "entity_type": "test",
                "description": "A complete test entity",
                "observations": ["First observation", "Second observation"],
            }
        ]
    }

    result = await server.handle_call_tool("create_entities", entity_data)
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)

    entity = response.entities[0]
    assert entity.name == "FullEntity"
    assert entity.description == "A complete test entity"
    assert len(entity.observations) == 2
    assert entity.observations[0].content == "First observation"
    assert entity.observations[1].content == "Second observation"


@pytest.mark.asyncio
async def test_list_tools(server):
    """Test that server exposes expected tools."""

    tools = await server.handle_list_tools()

    # Check each expected tool is present
    expected_tools = {
        "create_entities",
        "search_nodes",
        "open_nodes",
        "add_observations",
        "create_relations",
        "delete_entities",
        "delete_observations",
        "delete_relations",
    }

    found_tools = {t.name: t for t in tools}
    assert found_tools.keys() == expected_tools

    # Verify schemas include required fields
    search_schema = found_tools["search_nodes"].inputSchema
    assert "query" in search_schema["properties"]
    assert search_schema["required"] == ["query"]


@pytest.mark.asyncio
async def test_search_nodes(test_entity_data, client, server):
    """Test searching for an entity after creating it."""

    # First create an entity
    await server.handle_call_tool("create_entities", test_entity_data)

    # Then search for it
    result = await server.handle_call_tool("search_nodes", {"query": "Test Entity"})

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert isinstance(result[0].resource.uri, type(BASIC_MEMORY_URI))
    assert str(result[0].resource.uri) == str(BASIC_MEMORY_URI)
    assert result[0].resource.mimeType == MIME_TYPE

    # Verify search results
    response = SearchNodesResponse.model_validate_json(result[0].resource.text)
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
    create_response = CreateEntityResponse.model_validate_json(create_result[0].resource.text)
    entity_id = create_response.entities[0].id

    # Add new observation
    result = await server.handle_call_tool(
        "add_observations", {"entity_id": entity_id, "observations": ["A new observation"]}
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
async def test_create_relations(test_entity_data, client, server):
    """Test creating relations between entities."""
    # Create two test entities
    entity_data = {
        "entities": [
            {"name": "TestEntityA", "entity_type": "test", "observations": ["Entity A"]},
            {"name": "TestEntityB", "entity_type": "test", "observations": ["Entity B"]},
        ]
    }

    await server.handle_call_tool("create_entities", entity_data)

    # Create relation between them
    relation_data = {
        "relations": [
            {
                "from_id": "test/TestEntityA",
                "to_id": "test/TestEntityB",
                "relation_type": "relates_to",
            }
        ]
    }

    result = await server.handle_call_tool("create_relations", relation_data)

    # Verify through search
    search_result = await server.handle_call_tool("search_nodes", {"query": "TestEntityA"})
    response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)

    assert len(response.matches) == 1
    entity = response.matches[0]
    assert len(entity.relations) == 1
    assert entity.relations[0].to_id == normalize_entity_id("test/TestEntityB")
    assert entity.relations[0].relation_type == "relates_to"


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
