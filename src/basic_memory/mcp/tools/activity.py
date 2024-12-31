"""Tools for tracking activity and changes in the knowledge base."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.schemas.activity import ActivityType, RecentActivity


@mcp.tool(
    description="""
    Get recent activity across your knowledge base.

    This tool provides a comprehensive view of changes across your knowledge base,
    including document modifications, entity updates, and relationship changes.
    It supports flexible time ranges and filtering by activity type.

    The activity log helps you:
    - Track recent changes to your knowledge base
    - Monitor document and entity modifications
    - Understand system usage patterns
    - Identify most active areas

    Activity is tracked for:
    - Document changes (creation, updates, deletion)
    - Entity modifications 
    - Relation changes between entities
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
    output_schema={
        "description": "Complete activity report showing recent changes and summary statistics",
        "properties": {
            "timeframe": {
                "title": "Timeframe",
                "type": "string",
                "description": "Time period the activity covers (e.g. 1h, 1d, 1w, 1m)"
            },
            "changes": {
                "title": "Changes",
                "type": "array",
                "description": "List of individual changes in chronological order",
                "items": {
                    "$ref": "#/definitions/ActivityChange"
                }
            },
            "summary": {
                "$ref": "#/definitions/ActivitySummary",
                "description": "Aggregated statistics about changes"
            }
        },
        "definitions": {
            "ActivityChange": {
                "description": "Detailed record of a single change in the system",
                "properties": {
                    "activity_type": {
                        "type": "string",
                        "enum": ["document", "entity", "relation"],
                        "description": "Category of item that changed"
                    },
                    "change_type": {
                        "type": "string",
                        "enum": ["created", "updated", "deleted"],
                        "description": "Type of change that occurred"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "When the change happened (ISO format)"
                    },
                    "path_id": {
                        "type": "string",
                        "description": "Identifier for the changed item"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Human-readable description of the change"
                    },
                    "content": {
                        "type": "string",
                        "description": "Optional details about the change",
                        "nullable": True
                    }
                },
                "required": ["activity_type", "change_type", "timestamp", "path_id", "summary"]
            },
            "ActivitySummary": {
                "description": "Statistical overview of activity in the timeframe",
                "properties": {
                    "document_changes": {
                        "type": "integer",
                        "description": "Number of document modifications",
                        "default": 0
                    },
                    "entity_changes": {
                        "type": "integer",
                        "description": "Number of entity modifications",
                        "default": 0
                    },
                    "relation_changes": {
                        "type": "integer", 
                        "description": "Number of relationship changes",
                        "default": 0
                    },
                    "most_active_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of paths with most changes"
                    }
                }
            }
        }
    }
)
async def get_recent_activity(
    timeframe: str = "1d",
    activity_types: Optional[List[ActivityType]] = None,
) -> RecentActivity:
    """
    Get recent activity across your knowledge base.
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
