"""Router for knowledge graph operations."""
from fastapi import APIRouter

from basic_memory.deps import MemoryServiceDep
from basic_memory.schemas import (
    CreateEntityRequest, CreateEntityResponse,
    SearchNodesRequest, SearchNodesResponse,
    CreateRelationsRequest, CreateRelationsResponse,
    EntityResponse, AddObservationsRequest, ObservationResponse,
    OpenNodesRequest, OpenNodesResponse,
    DeleteEntityResponse,
    DeleteObservationsRequest, DeleteObservationsResponse, AddObservationsResponse, RelationResponse,
    DeleteRelationRequest
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/entities", response_model=CreateEntityResponse)
async def create_entities(
    data: CreateEntityRequest,
    memory_service: MemoryServiceDep
) -> CreateEntityResponse:
    """Create new entities in the knowledge graph."""
    entities = await memory_service.create_entities(data.entities)
    return CreateEntityResponse(entities=[EntityResponse.model_validate(entity) for entity in entities])


@router.get("/entities/{entity_id:path}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    memory_service: MemoryServiceDep
) -> EntityResponse:
    """Get a specific entity by ID."""
    entity = await memory_service.get_entity(entity_id)
    return EntityResponse.model_validate(entity)


@router.delete("/entities/{entity_id}", response_model=DeleteEntityResponse)
async def delete_entity(
    entity_id: str,
    memory_service: MemoryServiceDep
) -> DeleteEntityResponse:
    """Delete a specific entity by ID."""
    deleted = await memory_service.delete_entities([entity_id])
    return DeleteEntityResponse(deleted=deleted)  # pyright: ignore [reportArgumentType]


@router.post("/nodes", response_model=OpenNodesResponse)
async def open_nodes(
    data: OpenNodesRequest,
    memory_service: MemoryServiceDep
) -> OpenNodesResponse:
    """Open specific nodes by their names."""
    entities = await memory_service.open_nodes(data.names)
    return OpenNodesResponse(entities=[EntityResponse.model_validate(entity) for entity in entities])


@router.post("/relations", response_model=CreateRelationsResponse)
async def create_relations(
    data: CreateRelationsRequest,
    memory_service: MemoryServiceDep
) -> CreateRelationsResponse:
    """Create relations between entities."""
    relations = await memory_service.create_relations(data.relations)
    return CreateRelationsResponse(relations=[RelationResponse.model_validate(relation) for relation in relations])


@router.delete("/relations/{from_id:path}/{to_id:path}", response_model=DeleteEntityResponse)
async def delete_relation(
    memory_service: MemoryServiceDep,
    from_id: str,
    to_id: str,
    relation_type: str | None = None,
) -> DeleteEntityResponse:
    """Delete relations between entities, optionally filtered by type."""
    request = DeleteRelationRequest(from_id=from_id, to_id=to_id, relation_type=relation_type)
    deleted = await memory_service.delete_relations([request])
    return DeleteEntityResponse(deleted=deleted)


@router.post("/observations", response_model=AddObservationsResponse)
async def add_observations(
    data: AddObservationsRequest,
    memory_service: MemoryServiceDep
) -> AddObservationsResponse:
    """Add observations to an entity."""
    observations = await memory_service.add_observations(data)
    return AddObservationsResponse(entity_id=data.entity_id, observations=[ObservationResponse.model_validate(observation) for observation in observations])


@router.delete("/entities/{entity_id:path}/observations", response_model=DeleteObservationsResponse)
async def delete_observations(
    entity_id: str,
    data: DeleteObservationsRequest,
    memory_service: MemoryServiceDep
) -> DeleteObservationsResponse:
    """Delete observations from an entity."""
    # Ensure entity_id matches the request
    if data.entity_id != entity_id:
        data.entity_id = entity_id
    deleted = await memory_service.delete_observations(data)
    return DeleteObservationsResponse(deleted=deleted)


@router.post("/search", response_model=SearchNodesResponse)
async def search_nodes(
    data: SearchNodesRequest,
    memory_service: MemoryServiceDep
) -> SearchNodesResponse:
    """Search for entities in the knowledge graph."""
    matches = await memory_service.search_nodes(data.query)
    return SearchNodesResponse(matches=[EntityResponse.model_validate(entity) for entity in matches], query=data.query)
