"""Tools for discovering and analyzing knowledge graph structure."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList
from basic_memory.mcp.async_client import client


@mcp.tool()
async def get_entity_types() -> List[str]:
    """List all unique entity types in use across the knowledge graph.

    Examples:
        types = await get_entity_types()

        # Returns list of strings like:
        # [
        #     "technical_component",
        #     "specification",
        #     "decision",
        #     "feature"
        # ]

        Returns:
            List of unique entity type strings used in the knowledge graph
    """
    logger.debug("Getting all entity types")
    url = "/discovery/entity-types"
    response = await client.get(url)
    return EntityTypeList.model_validate(response.json())


@mcp.tool()
async def get_observation_categories() -> List[str]:
    """List all unique observation categories in use across the knowledge graph.

    Examples:
        categories = await get_observation_categories()

        # Returns list of strings like:
        # [
        #     "tech",
        #     "design",
        #     "feature",
        #     "note"
        # ]

        Returns:
            List of unique observation category strings used in the knowledge graph
    """
    logger.debug("Getting all observation categories")
    url = "/discovery/observation-categories"
    response = await client.get(url)
    return ObservationCategoryList.model_validate(response.json())


@mcp.tool()
async def list_by_type(
    entity_type: str, include_related: bool = False, sort_by: Optional[str] = "updated_at"
) -> TypedEntityList:
    """List all entities of a specific type.

    Example:
        # Get all features
        features = await list_by_type("feature")

        # Get components with relations
        components = await list_by_type(
            "component",
            include_related=True
        )
    """
    logger.debug(f"Listing entities of type: {entity_type}")
    params = {"include_related": "true" if include_related else "false"}
    if sort_by:
        params["sort_by"] = sort_by

    url = f"/discovery/entities/{entity_type}"
    response = await client.get(url, params=params)
    return TypedEntityList.model_validate(response.json())
