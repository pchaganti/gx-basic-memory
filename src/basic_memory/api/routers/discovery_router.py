"""Router for knowledge discovery and analytics operations."""

from typing import Optional

from fastapi import APIRouter
from loguru import logger

from basic_memory.deps import EntityServiceDep, ObservationServiceDep
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList, EntityResponse

router = APIRouter(prefix="/discovery", tags=["discovery"])




@router.get("/observation-categories", response_model=ObservationCategoryList)
async def get_observation_categories(observation_service: ObservationServiceDep) -> ObservationCategoryList:
    """Get list of all unique observation categories in the system."""
    logger.debug("Getting all observation categories")
    categories = await observation_service.observation_categories()
    return ObservationCategoryList(categories=categories)

