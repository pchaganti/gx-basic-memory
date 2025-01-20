"""Discussion context tools for Basic Memory MCP server."""

from typing import Optional, List

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.utils import call_get
from basic_memory.schemas.memory import GraphContext, MemoryUrl
from basic_memory.schemas.search import SearchItemType
from basic_memory.schemas.base import TimeFrame


@mcp.tool(
    description="""Build context from a memory:// URI to continue conversations naturally.
    
    Use this to follow up on previous discussions or explore related topics.
    Timeframes use natural language support - examples:
    - "2 days ago"
    - "last week" 
    - "today"
    - "3 months ago"
    Or standard formats like "7d", "24h"
    """,
)
async def build_context(
    url: MemoryUrl,
    depth: Optional[int] = 1,
    timeframe: Optional[TimeFrame] = "7d",
    max_results: int = 10,
) -> GraphContext:
    """Get context needed to continue a discussion.

    This tool enables natural continuation of discussions by loading relevant context
    from memory:// URIs. It uses pattern matching to find relevant content and builds
    a rich context graph of related information.

    Args:
        url: memory:// URI pointing to discussion content (e.g. memory://specs/search)
        depth: How many relation hops to traverse (1-3 recommended for performance)
        timeframe: How far back to look. Supports natural language like "2 days ago", "last week"
        max_results: Maximum number of results to return (default: 10)

    Returns:
        GraphContext containing:
            - primary_results: Content matching the memory:// URI
            - related_results: Connected content via relations
            - metadata: Context building details

    Examples:
        # Continue a specific discussion
        build_context("memory://specs/search")

        # Get deeper context about a component
        build_context("memory://components/memory-service", depth=2)

        # Look at recent changes to a specification
        build_context("memory://specs/document-format", timeframe="today")

        # Research the history of a feature
        build_context("memory://features/knowledge-graph", timeframe="3 months ago")
    """
    logger.info(f"Building context from {url}")
    # Map directly to the memory endpoint
    memory_url = MemoryUrl.validate(url)
    response = await call_get(
        client,
        f"/memory/{memory_url.relative_path()}",
        params={"depth": depth, "timeframe": timeframe, "max_results": max_results},
    )
    return GraphContext.model_validate(response.json())


@mcp.tool(
    description="""Get recent activity from across the knowledge base.
    
    Timeframe supports natural language formats like:
    - "2 days ago"
    - "last week"
    - "3 weeks"
    - "2 months"
    - "yesterday"
    - "today"
    Or standard formats like "7d", "24h"
    """,
)
async def recent_activity(
    types: List[SearchItemType] = None,
    depth: Optional[int] = 1,
    timeframe: Optional[TimeFrame] = "7d",
    max_results: int = 10,
) -> GraphContext:
    """Get recent activity across the knowledge base.

    Args:
        types: Filter by entity types (["entity", "relation", "observation"]). If None, returns all types.
        depth: How many relation hops to traverse when building context (1-3 recommended)
        timeframe: How far back to look. Supports natural language like "2 days ago", "last week"
        max_results: Maximum number of results to return (default: 10)

    Returns:
        GraphContext containing:
            - primary_results: Latest activities matching the filters
            - related_results: Connected content via relations
            - metadata: Query details and statistics

    Examples:
        # Get all activity from last week
        recent_activity(timeframe="last week")

        # Get only entity changes from yesterday
        recent_activity(types=["entity"], timeframe="yesterday")

        # Track recent specification changes
        recent_activity(types=["entity"], depth=2, timeframe="3 days ago")

        # Follow recent relation changes
        recent_activity(types=["relation"], timeframe="today")

    Notes:
        - Higher depth values (>3) may impact performance with large result sets
        - For focused queries, consider using build_context with a specific URI
        - Max timeframe is 1 year in the past
    """
    logger.info(
        f"Getting recent activity from {types}, depth={depth}, timeframe={timeframe}, max_results={max_results}"
    )
    response = await client.get(
        "/memory/recent",
        params={"depth": depth, "timeframe": timeframe, "max_results": max_results, "types": types},
    )
    return GraphContext.model_validate(response.json())
