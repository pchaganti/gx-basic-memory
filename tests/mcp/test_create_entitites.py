"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest
from mcp.types import EmbeddedResource

from basic_memory.mcp.server import MIME_TYPE, handle_call_tool
from basic_memory.schemas import CreateEntityResponse, SearchNodesResponse


@pytest.mark.asyncio
async def test_create_single_entity(app):
    """Test creating a single entity."""
    entity_data = {
        "entities": [
            {"name": "SingleTest", "entity_type": "test", "observations": ["Test observation"]}
        ]
    }

    result = await handle_call_tool("create_entities", entity_data)

    # Verify response format
    assert len(result) == 1
    assert isinstance(result[0], EmbeddedResource)
    assert result[0].type == "resource"
    assert result[0].resource.mimeType == MIME_TYPE

    # Verify entity creation
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
    assert len(response.entities) == 1
    entity = response.entities[0]
    assert entity.name == "SingleTest"
    assert entity.entity_type == "test"
    assert len(entity.observations) == 1
    assert entity.observations[0].content == "Test observation"
    assert entity.id == "test/singletest"

    # Verify entity can be found via search
    search_result = await handle_call_tool("search_nodes", {"query": "SingleTest"})
    search_response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
    assert len(search_response.matches) == 1
    assert search_response.matches[0].name == "SingleTest"


@pytest.mark.asyncio
async def test_create_multiple_entities(app):
    """Test creating multiple entities in one call."""
    entity_data = {
        "entities": [
            {"name": "BulkTest1", "entity_type": "test", "observations": ["First bulk test"]},
            {"name": "BulkTest2", "entity_type": "test", "observations": ["Second bulk test"]},
            {"name": "BulkTest3", "entity_type": "demo", "observations": ["Third bulk test"]},
        ]
    }

    result = await handle_call_tool("create_entities", entity_data)

    # Verify response
    assert len(result) == 1
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]

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
    search_result = await handle_call_tool("search_nodes", {"query": "BulkTest"})
    search_response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
    assert len(search_response.matches) == 3


@pytest.mark.asyncio
async def test_create_entity_with_all_fields(app):
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

    result = await handle_call_tool("create_entities", entity_data)
    response = CreateEntityResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]

    entity = response.entities[0]
    assert entity.name == "FullEntity"
    assert entity.description == "A complete test entity"
    assert len(entity.observations) == 2
    assert entity.observations[0].content == "First observation"
    assert entity.observations[1].content == "Second observation"
