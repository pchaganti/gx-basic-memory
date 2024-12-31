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
    activity_types: Optional[List[ActivityType]] = Query(None),
) -> RecentActivity:
    """
    Get recent activity across the knowledge base.

    Args:
        timeframe: Time window to look back (1h, 1d, 1w, 1m)
        activity_types: Optional list of ActivityType values to include

    Returns:
        RecentActivity with changes and summary
    """
    logger.debug(
        f"Getting recent activity (timeframe={timeframe}, "
        f"types={activity_types})"
    )

    return await activity_service.get_recent_activity(
        timeframe=timeframe,
        activity_types=[t.value for t in activity_types] if activity_types else None,
    )