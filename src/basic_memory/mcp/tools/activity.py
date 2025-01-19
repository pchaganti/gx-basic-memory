"""Tools for tracking activity and changes in the knowledge base."""

from typing import List, Optional

from loguru import logger
from mcp.server.fastmcp import Context

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.schemas.activity import ActivityType, RecentActivity


@mcp.tool(
    description="Track recent changes to documents, entities, and relations",
)
async def get_recent_activity(
    context: Context,
    timeframe: str = "1d",
    activity_types: Optional[List[ActivityType]] = None,
) -> RecentActivity:
    """Track changes across the knowledge base.

    Args:
        timeframe: Time window to analyze ("1h", "1d", "1w")
        activity_types: Optional list of types to filter by
        context: MCP context 

    Returns:
        RecentActivity object with changes and summary statistics
    """
    context.info(f"Getting recent activity (timeframe={timeframe}, types={activity_types})")

    # Build params
    params = {
        "timeframe": timeframe,
    }
    if activity_types:
        params["activity_types"] = [t.value for t in activity_types]

    # Get activity
    response = await client.get("/activity/recent", params=params)
    return RecentActivity.model_validate(response.json())
