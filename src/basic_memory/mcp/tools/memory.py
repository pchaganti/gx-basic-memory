"""Discussion context tools for Basic Memory MCP server."""

from typing import Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.schemas.memory import GraphContext, MemoryUrl


@mcp.tool(
    description="Build context from a memory:// URI to continue conversations naturally.",
)
async def build_context(
    url: MemoryUrl,
    depth: Optional[int] = 1,
    timeframe: Optional[str] = "7d",
    max_results: int = 10
) -> GraphContext:
    """Get context needed to continue a discussion.

    This tool enables natural continuation of discussions by loading relevant context
    from memory:// URIs. It uses pattern matching to find relevant content and builds
    a rich context graph of related information.

    Args:
        ctx: MCP context
        url: memory:// URI pointing to discussion content (e.g. memory://specs/search)
        depth: How many relation hops to traverse (default: 2)
        timeframe: How far back to look, e.g. "7d", "24h" (default: "7d")
        max_results: The maximum number of results to return (default: 10)

    Returns:
        GraphContext containing:
            - primary_entities: Directly matched content
            - related_entities: Connected content via relations
            - metadata: Context building info
    """
    logger.info(f"Building context from {url}")
    # Map directly to the memory endpoint
    memory_url = MemoryUrl.validate(url)
    response = await client.get(
        f"/memory/{memory_url.relative_path()}", params={"depth": depth, "timeframe": timeframe, "max_results": max_results}
    )
    return GraphContext.model_validate(response.json())