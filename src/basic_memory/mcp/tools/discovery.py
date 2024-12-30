"""Tools for discovering and analyzing knowledge graph structure."""

from typing import List

from loguru import logger

from basic_memory.schemas import EntityTypeList
from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp


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
    return EntityTypeList.model_validate(response.json()).types
