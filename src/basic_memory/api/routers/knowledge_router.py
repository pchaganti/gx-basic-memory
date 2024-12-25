"""Router for knowledge graph operations."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from basic_memory.deps import (
    EntityServiceDep,
    KnowledgeServiceDep,
)
from basic_memory.schemas import (
    CreateEntityRequest,
    EntityListResponse,
    SearchNodesRequest,
    SearchNodesResponse,
    CreateRelationsRequest,
    EntityResponse,
    AddObservationsRequest,
    OpenNodesRequest,
    DeleteEntitiesResponse,
    DeleteObservationsRequest,
    DeleteRelationsRequest,
    DeleteEntitiesRequest,
)
from basic_memory.schemas.base import PathId
from basic_memory.services.exceptions import EntityNotFoundError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

## Create endpoints


@router.post("/entities", response_model=EntityListResponse)
async def create_entities(
    data: CreateEntityRequest, knowledge_service: KnowledgeServiceDep
) -> EntityListResponse:
    """Create new entities in the knowledge graph."""
    entities = await knowledge_service.create_entities(data.entities)
    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


@router.post("/relations", response_model=EntityListResponse)
async def create_relations(
    data: CreateRelationsRequest, knowledge_service: KnowledgeServiceDep
) -> EntityListResponse:
    """Create relations between entities."""
    updated_entities = await knowledge_service.create_relations(data.relations)
    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in updated_entities]
    )


@router.post("/observations", response_model=EntityResponse)
async def add_observations(
    data: AddObservationsRequest, knowledge_service: KnowledgeServiceDep
) -> EntityResponse:
    """Add observations to an entity."""
    logger.debug(f"Adding observations to entity: {data.path_id}")
    updated_entity = await knowledge_service.add_observations(
        data.path_id, data.observations, data.context
    )
    return EntityResponse.model_validate(updated_entity)


## Read endpoints


@router.get("/entities/{path_id:path}", response_model=EntityResponse)
async def get_entity(path_id: PathId, entity_service: EntityServiceDep) -> EntityResponse:
    """Get a specific entity by ID."""
    try:
        entity = await entity_service.get_by_path_id(path_id)
        return EntityResponse.model_validate(entity)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Entity with {path_id} not found")


@router.post("/search", response_model=SearchNodesResponse)
async def search_nodes(
    data: SearchNodesRequest, entity_service: EntityServiceDep
) -> SearchNodesResponse:
    """Search for entities in the knowledge graph."""
    logger.debug(f"Searching nodes with query: {data.query}")
    matches = await entity_service.search(data.query)
    logger.debug(f"Found {len(matches)} matches for '{data.query}'")

    return SearchNodesResponse(
        matches=[EntityResponse.model_validate(entity) for entity in matches], query=data.query
    )


@router.post("/nodes", response_model=EntityListResponse)
async def open_nodes(data: OpenNodesRequest, entity_service: EntityServiceDep) -> EntityListResponse:
    """Open specific nodes by their names."""
    entities = await entity_service.open_nodes(data.path_ids)
    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


## Delete endpoints


@router.post("/entities/delete", response_model=DeleteEntitiesResponse)
async def delete_entities(
    data: DeleteEntitiesRequest, knowledge_service: KnowledgeServiceDep
) -> DeleteEntitiesResponse:
    """Delete a specific entity by PathId."""
    deleted = await knowledge_service.delete_entities(data.path_ids)
    return DeleteEntitiesResponse(deleted=deleted)


@router.post("/observations/delete", response_model=EntityResponse)
async def delete_observations(
    data: DeleteObservationsRequest, knowledge_service: KnowledgeServiceDep
) -> EntityResponse:
    """Delete observations from an entity."""
    path_id = data.path_id
    updated_entity = await knowledge_service.delete_observations(path_id, data.observations)
    return EntityResponse.model_validate(updated_entity)


@router.post("/relations/delete", response_model=EntityListResponse)
async def delete_relations(
    data: DeleteRelationsRequest, knowledge_service: KnowledgeServiceDep
) -> EntityListResponse:
    """Delete relations between entities."""
    updated_entities = await knowledge_service.delete_relations(data.relations)
    return EntityListResponse(
        entities=[EntityResponse.model_validate(entity) for entity in updated_entities]
    )
