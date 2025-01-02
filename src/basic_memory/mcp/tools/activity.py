"""Tools for tracking activity and changes in the knowledge base."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.schemas.activity import ActivityType, RecentActivity


@mcp.tool(
    category="activity",
    description="Track recent changes to documents, entities, and relations",
    examples=[
        {
            "name": "Activity Summary",
            "description": "Get a high-level overview of changes",
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
            "name": "Document Changes",
            "description": "Track document evolution over time",
            "code": """
# Get hourly document changes with context
docs = await get_recent_activity(
    timeframe="1h",
    activity_types=[ActivityType.DOCUMENT]
)

# Show document evolution chronologically
for change in sorted(docs.changes, key=lambda x: x.timestamp):
    print(f"{change.timestamp}: {change.path_id}")
    print(f"  {change.change_type}: {change.summary}")
"""
        },
        {
            "name": "Knowledge Evolution",
            "description": "Analyze how knowledge structure changes over time",
            "code": """
# Get weekly activity for change pattern analysis
weekly = await get_recent_activity(timeframe="1w")

# Group changes by type for pattern analysis
from collections import defaultdict
changes_by_type = defaultdict(list)
for change in weekly.changes:
    changes_by_type[change.activity_type].append(change)

# Analyze change distribution
for type_, changes in changes_by_type.items():
    print(f"{type_}: {len(changes)} changes")
    
# Find most modified entities
entity_changes = defaultdict(int)
for change in weekly.changes:
    if change.activity_type == "entity":
        entity_changes[change.path_id] += 1

print("\\nMost active entities:")
for path_id, count in sorted(
    entity_changes.items(), 
    key=lambda x: x[1], 
    reverse=True
)[:5]:
    print(f"- {path_id}: {count} changes")
"""
        },
        {
            "name": "Context Building",
            "description": "Use activity history to build rich context",
            "code": """
# Get recent activity across all types
activity = await get_recent_activity(timeframe="1d")

# Extract changed entities for deeper analysis
entity_ids = [
    change.path_id for change in activity.changes
    if change.activity_type == "entity"
]

# Load full entity details
if entity_ids:
    entities = await open_nodes(
        request=OpenNodesRequest(path_ids=entity_ids)
    )
    
    # Analyze recent development focus
    tech_changes = defaultdict(list)
    for entity in entities.entities:
        tech_obs = [o for o in entity.observations 
                   if o.category == "tech"]
        if tech_obs:
            tech_changes[entity.name] = tech_obs

    print("Recent technical changes:")
    for name, observations in tech_changes.items():
        print(f"\\n{name}:")
        for obs in observations:
            print(f"- {obs.content}")
"""
        }
    ],
    output_model=RecentActivity
)
async def get_recent_activity(
    timeframe: str = "1d",
    activity_types: Optional[List[ActivityType]] = None,
) -> RecentActivity:
    """Track changes across the knowledge base.
    
    Args:
        timeframe: Time window to analyze ("1h", "1d", "1w")
        activity_types: Optional list of types to filter by
        
    Returns:
        RecentActivity object with changes and summary statistics
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