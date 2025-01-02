"""Tools for tracking activity and changes in the knowledge base."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.schemas.activity import ActivityType, RecentActivity


@mcp.tool(
    category="activity",
    description="""Track recent changes to documents, entities, and relations.
    
    This tool provides visibility into knowledge base evolution by:
    - Monitoring document, entity, and relation changes
    - Tracking the chronological history of modifications
    - Analyzing patterns of knowledge development
    - Identifying active areas of development
    
    Activity tracking helps maintain context across AI-human collaboration sessions.
    """,
    examples=[
        {
            "name": "Daily Changes Overview",
            "description": "Get a summary of all changes in the last day",
            "code": """
# Get last 24 hours of activity
activity = await get_recent_activity()

# Print summary statistics
print(f"Total changes: {len(activity.changes)}")
print(f"Documents modified: {activity.summary.document_changes}")
print(f"Entities modified: {activity.summary.entity_changes}")
print(f"Relations changed: {activity.summary.relation_changes}")

# Show most active areas
print("\\nMost active paths:")
for path in activity.summary.most_active_paths:
    print(f"- {path}")
"""
        },
        {
            "name": "Filter Document Changes",
            "description": "Focus on recent document activity",
            "code": """
# Get only document changes from last hour
docs = await get_recent_activity(
    timeframe="1h",
    activity_types=[ActivityType.DOCUMENT]
)

# Show document changes chronologically
for change in sorted(docs.changes, key=lambda x: x.timestamp):
    print(f"{change.timestamp}: {change.path_id}")
    print(f"  {change.change_type}: {change.summary}")
"""
        },
        {
            "name": "Weekly Activity Analysis",
            "description": "Analyze patterns over past week",
            "code": """
# Get full week of activity
weekly = await get_recent_activity(timeframe="1w")

# Group changes by type
from collections import defaultdict
changes_by_type = defaultdict(list)
for change in weekly.changes:
    changes_by_type[change.activity_type].append(change)

# Show distribution
for type_, changes in changes_by_type.items():
    print(f"{type_}: {len(changes)} changes")
"""
        }
    ],
    output_model=RecentActivity
)
async def get_recent_activity(
    timeframe: str = "1d",
    activity_types: Optional[List[ActivityType]] = None,
) -> RecentActivity:
    """Get recent activity across your knowledge base.
    
    Args:
        timeframe: Time window to analyze, e.g., "1h", "1d", "1w"
        activity_types: Optional list of activity types to filter by
        
    Returns:
        RecentActivity object containing changes and summary statistics
    """
    logger.debug(f"Getting recent activity (timeframe={timeframe}, types={activity_types})")

    # Build params 
    params = {
        "timeframe": timeframe,
    }
    if activity_types:
        params["activity_types"] = [t.value for t in activity_types]

    # Get activity
    response = await client.get("/activity/recent", params=params)
    return RecentActivity.model_validate(response.json())