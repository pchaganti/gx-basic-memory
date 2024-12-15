"""Router for knowledge graph operations."""
from fastapi import APIRouter


from basic_memory.deps import MemoryServiceDep
from basic_memory.schemas import (
    CreateEntitiesInput, CreateEntitiesResponse,
    SearchNodesInput, SearchNodesResponse,
    CreateRelationsInput, CreateRelationsResponse,
    EntityOut, RelationOut, ObservationsIn, ObservationsOut, ObservationOut,
    OpenNodesInput, OpenNodesResponse,
    DeleteEntitiesResponse,
    DeleteObservationsInput, DeleteObservationsResponse
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/entities", response_model=CreateEntitiesResponse)
async def create_entities(
    data: CreateEntitiesInput,
    memory_service: MemoryServiceDep
) -> CreateEntitiesResponse:
    """Create new entities in the knowledge graph."""
    entities = await memory_service.create_entities(data.entities)
    return CreateEntitiesResponse(entities=[EntityOut.model_validate(entity) for entity in entities])


@router.get("/entities/{entity_id:path}", response_model=EntityOut)
async def get_entity(
    entity_id: str,
    memory_service: MemoryServiceDep
) -> EntityOut:
    """Get a specific entity by ID."""
    entity = await memory_service.get_entity(entity_id)
    return EntityOut.model_validate(entity)


@router.delete("/entities/{entity_id}", response_model=DeleteEntitiesResponse)
async def delete_entity(
    entity_id: str,
    memory_service: MemoryServiceDep
) -> DeleteEntitiesResponse:
    """Delete a specific entity by ID."""
    deleted = await memory_service.delete_entities([entity_id])
    return DeleteEntitiesResponse(deleted=deleted)  # pyright: ignore [reportArgumentType]


@router.post("/nodes", response_model=OpenNodesResponse)
async def open_nodes(
    data: OpenNodesInput,
    memory_service: MemoryServiceDep
) -> OpenNodesResponse:
    """Open specific nodes by their names."""
    entities = await memory_service.open_nodes(data.names)
    return OpenNodesResponse(entities=[EntityOut.model_validate(entity) for entity in entities])


@router.post("/relations", response_model=CreateRelationsResponse)
async def create_relations(
    data: CreateRelationsInput,
    memory_service: MemoryServiceDep
) -> CreateRelationsResponse:
    """Create relations between entities."""
    relations = await memory_service.create_relations(data.relations)
    return CreateRelationsResponse(relations=[RelationOut.model_validate(relation) for relation in relations])


@router.delete("/relations/{relation_id}", response_model=DeleteEntitiesResponse)
async def delete_relation(
    relation_id: int,
    memory_service: MemoryServiceDep
) -> DeleteEntitiesResponse:
    """Delete a specific relation by ID."""
    # TODO: Implement delete_relation in memory service
    raise NotImplementedError("Delete relation not implemented yet")


@router.post("/observations", response_model=ObservationsOut)
async def add_observations(
    data: ObservationsIn,
    memory_service: MemoryServiceDep
) -> ObservationsOut:
    """Add observations to an entity."""
    observations = await memory_service.add_observations(data)
    return ObservationsOut(entity_id=data.entity_id, observations=[ObservationOut.model_validate(observation) for observation in observations])


@router.delete("/observations", response_model=DeleteObservationsResponse)
async def delete_observations(
    data: DeleteObservationsInput,
    memory_service: MemoryServiceDep
) -> DeleteObservationsResponse:
    """Delete observations from an entity."""
    # TODO: Implement delete_observations in memory service
    raise NotImplementedError("Delete observations not implemented yet")


@router.post("/search", response_model=SearchNodesResponse)
async def search_nodes(
    data: SearchNodesInput,
    memory_service: MemoryServiceDep
) -> SearchNodesResponse:
    """Search for entities in the knowledge graph."""
    matches = await memory_service.search_nodes(data.query)
    return SearchNodesResponse(matches=[EntityOut.model_validate(entity) for entity in matches], query=data.query)