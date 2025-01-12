"""Router for knowledge graph operations."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from loguru import logger

from basic_memory.deps import (
    EntityServiceDep,
    get_search_service, RelationServiceDep, ObservationServiceDep, FileServiceDep,
)
from basic_memory.schemas import (
    CreateEntityRequest,
    EntityListResponse,
    CreateRelationsRequest,
    EntityResponse,
    AddObservationsRequest,
    OpenNodesRequest,
    DeleteEntitiesResponse,
    DeleteObservationsRequest,
    DeleteRelationsRequest,
    DeleteEntitiesRequest,
    UpdateEntityRequest,
)
from basic_memory.schemas.base import PathId
from basic_memory.services.exceptions import EntityNotFoundError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

## Create endpoints


@router.post("/entities", response_model=EntityListResponse)
async def create_entities(
    data: CreateEntityRequest,
    background_tasks: BackgroundTasks,
    entity_service: EntityServiceDep,
    search_service=Depends(get_search_service),
) -> EntityListResponse:
    """Create new entities in the knowledge graph and index them."""
    entities = await entity_service.create_entities(data.entities)

    # Index each entity
    for entity in entities:
        await search_service.index_entity(entity, background_tasks=background_tasks)

    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


@router.put("/entities/{path_id:path}", response_model=EntityResponse)
async def update_entity(
    path_id: PathId,
    data: UpdateEntityRequest,
    background_tasks: BackgroundTasks,
    entity_service: EntityServiceDep,
    search_service=Depends(get_search_service),
) -> EntityResponse:
    """Update an existing entity and reindex it."""
    try:
        # Convert request to dict, excluding None values
        update_data = data.model_dump(exclude_none=True)

        # Update the entity
        updated_entity = await entity_service.update_entity(path_id, **update_data)

        # Reindex since content changed
        await search_service.index_entity(updated_entity, background_tasks=background_tasks)

        return EntityResponse.model_validate(updated_entity)

    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Entity with {path_id} not found")


@router.post("/relations", response_model=EntityListResponse)
async def create_relations(
    data: CreateRelationsRequest,
    background_tasks: BackgroundTasks,
    relation_service: RelationServiceDep,
    search_service=Depends(get_search_service),
) -> EntityListResponse:
    """Create relations between entities and update search index."""
    updated_entities = await relation_service.create_relations(data.relations)

    # Reindex updated entities since relations have changed
    for entity in updated_entities:
        await search_service.index_entity(entity, background_tasks=background_tasks)

    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in updated_entities]
    )


@router.post("/observations", response_model=EntityResponse)
async def add_observations(
    data: AddObservationsRequest,
    background_tasks: BackgroundTasks,
    observation_service: ObservationServiceDep,
    search_service=Depends(get_search_service),
) -> EntityResponse:
    """Add observations to an entity and update search index."""
    logger.debug(f"Adding observations to entity: {data.path_id}")
    updated_entity = await observation_service.add_observations(
        data.path_id, data.observations, data.context
    )

    # Reindex the entity with new observations
    await search_service.index_entity(updated_entity, background_tasks=background_tasks)

    return EntityResponse.model_validate(updated_entity)


## Read endpoints


@router.get("/entities/{path_id:path}", response_model=EntityResponse)
async def get_entity(
        entity_service: EntityServiceDep,
        file_service: FileServiceDep,
        path_id: PathId,
        content: bool = False,  # New parameter
) -> EntityResponse:
    """Get a specific entity by ID.

    Args:
        path_id: Entity path ID
        content: If True, include full file content
        :param entity_service: EntityService
    """
    try:
        entity = await entity_service.get_by_path_id(path_id)
        entity_response = EntityResponse.model_validate(entity)

        if content:  # Load content if requested
            content = await file_service.read_entity_content(entity)
            entity_response.content = content

        return entity_response
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Entity with {path_id} not found")

@router.post("/nodes", response_model=EntityListResponse)
async def open_nodes(
    data: OpenNodesRequest, entity_service: EntityServiceDep
) -> EntityListResponse:
    """Open specific nodes"""
    entities = await entity_service.open_nodes(data.path_ids)
    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


## Delete endpoints


@router.post("/entities/delete", response_model=DeleteEntitiesResponse)
async def delete_entities(
    data: DeleteEntitiesRequest,
    background_tasks: BackgroundTasks,
    entity_service: EntityServiceDep,
    search_service=Depends(get_search_service),
) -> DeleteEntitiesResponse:
    """Delete entities and remove from search index."""
    deleted = await entity_service.delete_entities(data.path_ids)

    # Remove each deleted entity from search index
    for path_id in data.path_ids:
        background_tasks.add_task(search_service.delete_by_path_id, path_id)

    return DeleteEntitiesResponse(deleted=deleted)


@router.post("/observations/delete", response_model=EntityResponse)
async def delete_observations(
    data: DeleteObservationsRequest,
    background_tasks: BackgroundTasks,
    observation_service: ObservationServiceDep,
    search_service=Depends(get_search_service),
) -> EntityResponse:
    """Delete observations and update search index."""
    path_id = data.path_id
    updated_entity = await observation_service.delete_observations(path_id, data.observations)

    # Reindex the entity since observations changed
    await search_service.index_entity(updated_entity, background_tasks=background_tasks)

    return EntityResponse.model_validate(updated_entity)


@router.post("/relations/delete", response_model=EntityListResponse)
async def delete_relations(
    data: DeleteRelationsRequest,
    background_tasks: BackgroundTasks,
    relation_service: RelationServiceDep,
    search_service=Depends(get_search_service),
) -> EntityListResponse:
    """Delete relations and update search index."""
    updated_entities = await relation_service.delete_relations(data.relations)

    # Reindex entities since relations changed
    for entity in updated_entities:
        await search_service.index_entity(entity, background_tasks=background_tasks)

    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in updated_entities]
    )
