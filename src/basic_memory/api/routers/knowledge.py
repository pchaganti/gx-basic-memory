"""Router for knowledge graph operations."""

from fastapi import APIRouter, HTTPException

from basic_memory.deps import MemoryServiceDep
from basic_memory.fileio import EntityNotFoundError
from basic_memory.schemas import (
    CreateEntityRequest,
    CreateEntityResponse,
    SearchNodesRequest,
    SearchNodesResponse,
    CreateRelationsRequest,
    CreateRelationsResponse,
    EntityResponse,
    AddObservationsRequest,
    ObservationResponse,
    OpenNodesRequest,
    OpenNodesResponse,
    DeleteEntityResponse,
    DeleteObservationsRequest,
    DeleteObservationsResponse,
    DeleteRelationsRequest,
    DeleteRelationsResponse,
    AddObservationsResponse,
    RelationResponse,
    DeleteEntityRequest,
    Entity,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

## Create endpoints


@router.post("/entities", response_model=CreateEntityResponse)
async def create_entities(
    data: CreateEntityRequest, memory_service: MemoryServiceDep
) -> CreateEntityResponse:
    """Create new entities in the knowledge graph."""
    entities = await memory_service.create_entities(data.entities)
    return CreateEntityResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


@router.post("/relations", response_model=CreateRelationsResponse)
async def create_relations(
    data: CreateRelationsRequest, memory_service: MemoryServiceDep
) -> CreateRelationsResponse:
    """Create relations between entities."""
    relations = await memory_service.create_relations(data.relations)
    return CreateRelationsResponse(
        relations=[RelationResponse.model_validate(relation) for relation in relations]
    )


@router.post("/observations", response_model=AddObservationsResponse)
async def add_observations(
    data: AddObservationsRequest, memory_service: MemoryServiceDep
) -> AddObservationsResponse:
    """Add observations to an entity."""
    observations = await memory_service.add_observations(data)
    return AddObservationsResponse(
        entity_id=data.entity_id,
        observations=[
            ObservationResponse.model_validate(observation) for observation in observations
        ],
    )


## Read endpoints


@router.get("/entities/{entity_id:path}", response_model=EntityResponse)
async def get_entity(entity_id: str, memory_service: MemoryServiceDep) -> EntityResponse:
    """Get a specific entity by ID."""
    try:
        entity = await memory_service.get_entity(entity_id)
        return EntityResponse.model_validate(entity)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")


@router.post("/search", response_model=SearchNodesResponse)
async def search_nodes(
    data: SearchNodesRequest, memory_service: MemoryServiceDep
) -> SearchNodesResponse:
    """Search for entities in the knowledge graph."""
    matches = await memory_service.search_nodes(data.query)
    return SearchNodesResponse(
        matches=[EntityResponse.model_validate(entity) for entity in matches], query=data.query
    )


@router.post("/nodes", response_model=OpenNodesResponse)
async def open_nodes(data: OpenNodesRequest, memory_service: MemoryServiceDep) -> OpenNodesResponse:
    """Open specific nodes by their names."""
    entities = await memory_service.open_nodes(data.entity_ids)
    return OpenNodesResponse(entities=[Entity.model_validate(entity) for entity in entities])


## Delete endpoints


@router.post("/entities/delete", response_model=DeleteEntityResponse)
async def delete_entity(
    data: DeleteEntityRequest, memory_service: MemoryServiceDep
) -> DeleteEntityResponse:
    """Delete a specific entity by ID."""
    deleted = await memory_service.delete_entities(data.entity_ids)
    return DeleteEntityResponse(deleted=deleted)


@router.post("/observations/delete", response_model=DeleteObservationsResponse)
async def delete_observations(
    data: DeleteObservationsRequest, memory_service: MemoryServiceDep
) -> DeleteObservationsResponse:
    """Delete observations from an entity."""
    entity_id = data.entity_id
    deleted = await memory_service.delete_observations(entity_id, data.deletions)
    return DeleteObservationsResponse(deleted=deleted)


@router.post("/relations/delete", response_model=DeleteRelationsResponse)
async def delete_relations(
    data: DeleteRelationsRequest, memory_service: MemoryServiceDep
) -> DeleteRelationsResponse:
    """Delete relations between entities."""
    to_delete = [
        {
            "from_id": relation.from_id,
            "to_id": relation.to_id,
            "relation_type": relation.relation_type,
        }
        for relation in data.relations
    ]
    deleted = await memory_service.delete_relations(to_delete)
    return DeleteRelationsResponse(deleted=deleted)
