"""Router for knowledge graph operations."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from basic_memory.deps import (
    EntityServiceDep,
    KnowledgeServiceDep,
)
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
    DeleteEntitiesResponse,
    DeleteObservationsRequest,
    DeleteObservationsResponse,
    DeleteRelationsRequest,
    DeleteRelationsResponse,
    AddObservationsResponse,
    RelationResponse,
    DeleteEntitiesRequest,
)
from basic_memory.services.exceptions import EntityNotFoundError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

## Create endpoints


@router.post("/entities", response_model=CreateEntityResponse)
async def create_entities(
    data: CreateEntityRequest, knowledge_service: KnowledgeServiceDep
) -> CreateEntityResponse:
    """Create new entities in the knowledge graph."""
    entities = await knowledge_service.create_entities(data.entities)
    return CreateEntityResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


@router.post("/relations", response_model=CreateRelationsResponse)
async def create_relations(
    data: CreateRelationsRequest, knowledge_service: KnowledgeServiceDep
) -> CreateRelationsResponse:
    """Create relations between entities."""
    relations = await knowledge_service.create_relations(data.relations)
    return CreateRelationsResponse(
        relations=[RelationResponse.model_validate(relation) for relation in relations]
    )


@router.post("/observations", response_model=AddObservationsResponse)
async def add_observations(
    data: AddObservationsRequest, knowledge_service: KnowledgeServiceDep
) -> AddObservationsResponse:
    """Add observations to an entity."""
    logger.debug(f"Adding observations to entity: {data.entity_id}")
    observations = await knowledge_service.add_observations(
        data.entity_id, data.observations, data.context
    )
    return AddObservationsResponse(
        entity_id=data.entity_id,
        observations=[
            ObservationResponse.model_validate(observation) for observation in observations
        ],
    )


## Read endpoints


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: int, entity_service: EntityServiceDep) -> EntityResponse:
    """Get a specific entity by ID."""
    try:
        entity = await entity_service.get_entity(entity_id)
        return EntityResponse.model_validate(entity)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")


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


@router.post("/nodes", response_model=OpenNodesResponse)
async def open_nodes(data: OpenNodesRequest, entity_service: EntityServiceDep) -> OpenNodesResponse:
    """Open specific nodes by their names."""
    entities = await entity_service.open_nodes(data.entity_ids)
    return OpenNodesResponse(
        entities=[EntityResponse.model_validate(entity) for entity in entities]
    )


## Delete endpoints


@router.post("/entities/delete", response_model=DeleteEntitiesResponse)
async def delete_entity(
    data: DeleteEntitiesRequest, knowledge_service: KnowledgeServiceDep
) -> DeleteEntitiesResponse:
    """Delete a specific entity by ID."""
    deleted = await knowledge_service.delete_entities(data.entity_ids)
    return DeleteEntitiesResponse(deleted=deleted)


@router.post("/observations/delete", response_model=DeleteObservationsResponse)
async def delete_observations(
    data: DeleteObservationsRequest, knowledge_service: KnowledgeServiceDep
) -> DeleteObservationsResponse:
    """Delete observations from an entity."""
    entity_id = data.entity_id
    deleted = await knowledge_service.delete_observations(entity_id, data.deletions)
    return DeleteObservationsResponse(deleted=deleted)


@router.post("/relations/delete", response_model=DeleteRelationsResponse)
async def delete_relations(
    data: DeleteRelationsRequest, knowledge_service: KnowledgeServiceDep
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
    deleted = await knowledge_service.delete_relations(to_delete)
    return DeleteRelationsResponse(deleted=deleted)
