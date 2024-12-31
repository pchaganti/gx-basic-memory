"""Tools for tracking activity and changes in the knowledge base."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.tools.enhanced import enhanced_tool
from basic_memory.schemas.activity import ActivityType, RecentActivity


@enhanced_tool()
async def get_recent_activity(
    timeframe: str = "1d",
    activity_types: Optional[List[ActivityType]] = None,
) -> RecentActivity:
    """
    Get recent activity across your knowledge base.

    Shows you what has changed recently including:
    - Document changes
    - Entity updates
    - Relation modifications

    You can filter by:
    - Timeframe (e.g., 1h, 1d, 1w, 1m)
    - Activity types (document, entity, relation)

    Examples:
        # Get all activity in last day
        activity = await get_recent_activity()

        # Get only document changes
        docs = await get_recent_activity(
            timeframe="1h",
            activity_types=[ActivityType.DOCUMENT]
        )

        Returns:
            RecentActivity object with changes and summary
    """
    logger.debug(f"Getting recent activity (timeframe={timeframe}, " f"types={activity_types})")

    # Build params
    params = {
        "timeframe": timeframe,
    }
    if activity_types:
        params["activity_types"] = [t.value for t in activity_types]

    # Get activity
    response = await client.get("/activity/recent", params=params)
    return RecentActivity.model_validate(response.json())
