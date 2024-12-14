"""Router for knowledge graph operations."""
from fastapi import APIRouter


from basic_memory.api.deps import MemoryServiceDep
from basic_memory.schemas import (
    CreateEntitiesInput, CreateEntitiesResponse,
    SearchNodesInput, SearchNodesResponse,
    CreateRelationsInput, CreateRelationsResponse,
    EntityOut, RelationOut, ObservationsIn, ObservationsOut, ObservationOut
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

@router.get("/entities/{entity_id}", response_model=EntityOut)
async def get_entity(
    entity_id: str,
    memory_service: MemoryServiceDep
) -> EntityOut:
    """Get a specific entity by ID."""
    entity = await memory_service.get_entity(entity_id)
    return EntityOut.model_validate(entity)

@router.post("/relations", response_model=CreateRelationsResponse)
async def create_relations(
    data: CreateRelationsInput,
    memory_service: MemoryServiceDep
) -> CreateRelationsResponse:
    """Create relations between entities."""
    relations = await memory_service.create_relations(data.relations)
    return CreateRelationsResponse(relations=[RelationOut.model_validate(relation) for relation in relations])

@router.post("/observations", response_model=ObservationsOut)
async def add_observations(
    data: ObservationsIn,
    memory_service: MemoryServiceDep
) -> ObservationsOut:
    """Add observations to an entity."""
    observations = await memory_service.add_observations(data)
    return ObservationsOut(entity_id=data.entity_id, observations=[ObservationOut.model_validate(observation) for observation in observations])  # pyright: ignore [reportCallIssue]

@router.post("/search", response_model=SearchNodesResponse)
async def search_nodes(
    data: SearchNodesInput,
    memory_service: MemoryServiceDep
) -> SearchNodesResponse:
    """Search for entities in the knowledge graph."""
    matches = await memory_service.search_nodes(data.query)
    return SearchNodesResponse(matches=[EntityOut.model_validate(entity) for entity in matches], query=data.query)
