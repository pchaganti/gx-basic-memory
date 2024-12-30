"""Router for knowledge discovery and analytics operations."""

from fastapi import APIRouter
from loguru import logger

from basic_memory.deps import EntityServiceDep, ObservationServiceDep
from basic_memory.schemas import EntityTypeList, ObservationCategoryList

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/entity-types", response_model=EntityTypeList)
async def get_entity_types(entity_service: EntityServiceDep) -> EntityTypeList:
    """Get list of all unique entity types in the system."""
    logger.debug("Getting all entity types")
    types = await entity_service.get_entity_types()
    return EntityTypeList(types=types)


@router.get("/observation-categories", response_model=ObservationCategoryList)
async def get_observation_categories(observation_service: ObservationServiceDep) -> ObservationCategoryList:
    """Get list of all unique observation categories in the system."""
    logger.debug("Getting all observation categories")
    categories = await observation_service.observation_categories()
    return ObservationCategoryList(categories=categories)
