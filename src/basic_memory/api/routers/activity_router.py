"""Activity router for tracking recent changes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger

from basic_memory.deps import get_activity_service
from basic_memory.services.activity_service import ActivityService
from basic_memory.schemas.activity import RecentActivity, ActivityType


router = APIRouter(
    prefix="/activity",
    tags=["activity"]
)


@router.get(
    "/recent",
    response_model=RecentActivity,
    summary="Get recent activity"
)
async def get_recent_activity(
    activity_service: ActivityService = Depends(get_activity_service),
    timeframe: str = "1d",
    activity_types: Optional[List[str]] = Query(None),  # Use Query for array params
    include_content: bool = True
) -> RecentActivity:
    """
    Get recent activity across the knowledge base.

    Args:
        timeframe: Time window to look back (1h, 1d, 1w, 1m)
        activity_types: Optional list of types to include
        include_content: Whether to include full content

    Returns:
        RecentActivity with changes and summary
    """
    logger.debug(
        f"Getting recent activity (timeframe={timeframe}, "
        f"types={activity_types}, include_content={include_content})"
    )

    return await activity_service.get_recent_activity(
        timeframe=timeframe,
        activity_types=activity_types,
        include_content=include_content
    )