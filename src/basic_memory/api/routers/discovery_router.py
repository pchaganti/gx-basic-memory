"""Router for knowledge discovery and analytics operations."""

from typing import Optional

from fastapi import APIRouter
from loguru import logger

from basic_memory.deps import EntityServiceDep, ObservationServiceDep
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList, EntityResponse

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


@router.get("/entities/{entity_type}", response_model=TypedEntityList)
async def list_entities_by_type(
    entity_service: EntityServiceDep,
    entity_type: str,
    include_related: bool = False,
    sort_by: Optional[str] = "updated_at",
) -> TypedEntityList:
    """List all entities of a specific type."""
    logger.debug(f"Listing entities of type: {entity_type}")
    entities = await entity_service.list_entities(
        entity_type=entity_type,
        sort_by=sort_by,
        include_related=include_related
    )
    return TypedEntityList(
        entity_type=entity_type,
        entities=[EntityResponse.model_validate(e) for e in entities],
        total=len(entities),
        sort_by=sort_by,
        include_related=include_related
    )