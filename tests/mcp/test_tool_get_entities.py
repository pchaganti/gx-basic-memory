"""Tests for open_nodes MCP tool."""

import pytest
from httpx import AsyncClient
from mcp.server import FastMCP
from mcp.server.fastmcp import Context
from mcp.types import TextContent

from basic_memory.mcp.tools import get_entities
from basic_memory.mcp.tools.knowledge import create_entities
from basic_memory.schemas import EntityListResponse
from basic_memory.schemas.base import Entity
from basic_memory.schemas.request import CreateEntityRequest, GetEntitiesRequest


@pytest.mark.asyncio
async def test_open_multiple_entities(mcp: FastMCP, client: AsyncClient):
    """Test opening multiple entities."""
    # Create some test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="Entity1", entity_type="test", summary="First test entity"),
            Entity(title="Entity2", entity_type="test", summary="Second test entity"),
        ]
    )
    result = await mcp.call_tool("create_entities",{ "request": entity_request})

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    text_result = TextContent.model_validate(result[0]).text
    create_result = EntityListResponse.model_validate_json(text_result)
    permalinks = [e.permalink for e in create_result.entities]

    # Open the nodes
    request = GetEntitiesRequest(permalinks=permalinks)
    result = await get_entities(request)
    assert isinstance(result, EntityListResponse)
    response = EntityListResponse.model_validate(result)

    # Verify we got a dictionary with both entities
    assert len(response.entities) == 2

    for response_entity in response.entities:
        assert response_entity.permalink in permalinks
        assert response_entity.title in ["Entity1", "Entity2"]


@pytest.mark.asyncio
async def test_open_nodes_with_details(client):
    """Test that opened nodes have all their details."""
    # Create an entity with observations
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                title="DetailedEntity",
                entity_type="test",
                summary="Test entity with details",
                observations=["First observation", "Second observation"],
            )
        ]
    )
    create_result = await create_entities(entity_request)
    permalink = create_result.entities[0].permalink

    # Open the node
    request = GetEntitiesRequest(permalinks=[permalink])
    result = await get_entities(request)
    response = EntityListResponse.model_validate(result)

    # Verify all details are present
    entity = response.entities[0]
    assert entity.title == "DetailedEntity"
    assert entity.entity_type == "test"
    assert entity.summary == "Test entity with details"
    assert len(entity.observations) == 2


@pytest.mark.asyncio
async def test_open_nodes_with_relations(client):
    """Test opening nodes that have relations."""
    # Create related entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(title="Service", entity_type="test", summary="A service"),
            Entity(title="Database", entity_type="test", summary="A database"),
        ]
    )
    create_result = await create_entities(entity_request)
    permalinks = [e.permalink for e in create_result.entities]

    # Add a relation between them
    from basic_memory.mcp.tools.knowledge import create_relations
    from basic_memory.schemas.request import CreateRelationsRequest
    from basic_memory.schemas.base import Relation

    relation_request = CreateRelationsRequest(
        relations=[Relation(from_id=permalinks[0], to_id=permalinks[1], relation_type="depends_on")]
    )
    await create_relations(relation_request)

    # Open both nodes
    request = GetEntitiesRequest(permalinks=permalinks)
    result = await get_entities(request)
    response = EntityListResponse.model_validate(result)

    # Verify relations are present
    assert len(response.entities[0].relations) == 1
    assert len(response.entities[1].relations) == 1


@pytest.mark.asyncio
async def test_open_nonexistent_nodes(client):
    """Test behavior when some requested nodes don't exist."""
    # First create one real entity
    entity_request = CreateEntityRequest(entities=[Entity(title="RealEntity", entity_type="test")])
    create_result = await create_entities(entity_request)
    real_permalink = create_result.entities[0].permalink

    # Try to open both real and non-existent
    request = GetEntitiesRequest(permalinks=[real_permalink, "nonexistent"])
    result = await get_entities(request)
    response = EntityListResponse.model_validate(result)

    # Should only get the real entity back
    assert len(response.entities) == 1
    assert real_permalink in response.entities[0].permalink


@pytest.mark.asyncio
async def test_open_single_entity(client):
    """Test behavior with single permalink."""
    # Create an entity
    entity_request = CreateEntityRequest(
        entities=[Entity(title="SingleEntity", entity_type="test")]
    )
    create_result = await create_entities(entity_request)
    permalink = create_result.entities[0].permalink

    # Open just one node
    request = GetEntitiesRequest(permalinks=[permalink])
    result = await get_entities(request)
    response = EntityListResponse.model_validate(result)

    # Should get just that entity
    assert len(response.entities) == 1
    assert permalink in response.entities[0].permalink
