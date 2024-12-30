"""Router for knowledge discovery and analytics operations."""

from fastapi import APIRouter
from loguru import logger

from basic_memory.deps import EntityServiceDep
from basic_memory.schemas import EntityTypeList, ObservationCategoryList

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/entity-types", response_model=EntityTypeList)
async def get_entity_types(entity_service: EntityServiceDep) -> EntityTypeList:
    """Get list of all unique entity types in the system."""
    logger.debug("Getting all entity types")
    types = await entity_service.get_entity_types()
    return EntityTypeList(types=types)
