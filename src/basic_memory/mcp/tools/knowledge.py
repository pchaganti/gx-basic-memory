"""Knowledge graph management tools for Basic Memory MCP server."""

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.utils import call_get, call_post
from basic_memory.schemas.base import PathId
from basic_memory.schemas.request import (
    CreateEntityRequest,
    CreateRelationsRequest,
    GetEntitiesRequest,
)
from basic_memory.schemas.delete import (
    DeleteEntitiesRequest,
)
from basic_memory.schemas.response import EntityListResponse, EntityResponse, DeleteEntitiesResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="Create new entities in the knowledge graph with names, types, and observations",
)
async def create_entities(request: CreateEntityRequest) -> EntityListResponse:
    """Create new entities in the knowledge graph."""
    logger.info(f"Creating {len(request.entities)} entities")
    url = "/knowledge/entities"
    response = await call_post(client, url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())



@mcp.tool(
    description="Get complete information about a specific entity including observations and relations",
)
async def get_entity(permalink: PathId) -> EntityResponse:
    """Get a specific entity info by its permalink.

    Args:
        permalink: Path identifier for the entity
    """
    url = f"/knowledge/entities/{permalink}"
    response = await call_get(client, url)
    return EntityResponse.model_validate(response.json())


@mcp.tool(
    description="Load multiple entities by their permalinks in a single request",
)
async def get_entities(request: GetEntitiesRequest) -> EntityListResponse:
    """Load multiple entities by their permalinks.

    Args:
        request: OpenNodesRequest containing list of permalinks to load

    Returns:
        EntityListResponse containing complete details for each requested entity
    """
    url = "/knowledge/entities"
    response = await call_get(
        client, url, params=[("permalink", permalink) for permalink in request.permalinks]
    )
    return EntityListResponse.model_validate(response.json())



@mcp.tool(
    description="Permanently delete entities and all related content (observations and relations)",
)
async def delete_entities(request: DeleteEntitiesRequest) -> DeleteEntitiesResponse:
    """Delete entities from the knowledge graph."""
    url = "/knowledge/entities/delete"
    response = await call_post(client,url, json=request.model_dump())
    return DeleteEntitiesResponse.model_validate(response.json())
