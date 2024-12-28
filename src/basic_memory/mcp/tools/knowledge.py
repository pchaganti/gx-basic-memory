"""Knowledge graph management tools for Basic Memory MCP server."""

from typing import Dict

import httpx

from basic_memory.schemas.base import Entity, Relation, ObservationCategory, PathId
from basic_memory.schemas.request import (
    CreateEntityRequest,
    CreateRelationsRequest,
    AddObservationsRequest,
)
from basic_memory.schemas.delete import (
    DeleteEntitiesRequest,
    DeleteObservationsRequest,
    DeleteRelationsRequest
)
from basic_memory.schemas.response import EntityListResponse, EntityResponse
from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.services.exceptions import EntityNotFoundError


@mcp.tool()
async def get_entity(path_id: PathId) -> EntityResponse:
    """Get a specific entity by its path_id.
    
    Examples:
        # Load implementation details
        response = await get_entity("component/memory_service")
        
        # Response contains complete entity:
        # EntityResponse(
        #     path_id="component/memory_service",
        #     name="memory_service",
        #     entity_type="component",
        #     description="Core knowledge persistence service",
        #     observations=[
        #         Observation(
        #             category="TECH",
        #             content="Using SQLite for storage",
        #             context="Initial implementation"
        #         ),
        #         ...
        #     ],
        #     relations=[
        #         Relation(
        #             from_id="component/memory_service",
        #             to_id="component/file_service",
        #             relation_type="depends_on"
        #         ),
        #         ...
        #     ]
        # )

        # Load and analyze a design spec
        spec = await get_entity("specification/file_format")
        decisions = [obs for obs in spec.observations 
                    if obs.category == ObservationCategory.DESIGN]
    """
    try:
        url = f"/knowledge/entities/{path_id}"
        response = await client.get(url)
        if response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        response.raise_for_status()
        return EntityResponse.model_validate(response.json())
    except httpx.HTTPStatusError as e:
        # If we got a 404, the entity doesn't exist
        if e.response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        # For any other HTTP error, re-raise
        raise


@mcp.tool()
async def create_entities(request: CreateEntityRequest) -> EntityListResponse:
    """Create new entities in the knowledge graph.
    
    Examples:
        # Create a component with implementation details
        request = CreateEntityRequest(
            entities=[
                Entity(
                    name="memory_service",
                    entity_type="component",
                    description="Core service for knowledge persistence",
                    observations=[
                        "Using SQLite for storage",
                        "Implements filesystem as source of truth",
                        "Handles atomic file operations"
                    ]
                )
            ]
        )
        response = await create_entities(request)
        
        # Response contains full entity details:
        # EntityListResponse(
        #     entities=[
        #         EntityResponse(
        #             path_id="component/memory_service",
        #             name="memory_service",
        #             entity_type="component",
        #             description="Core service for knowledge persistence",
        #             observations=[...],  # List[Observation]
        #             relations=[]  # Empty for new entities
        #         )
        #     ]
        # )
    """
    url = "/knowledge/entities"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool()
async def create_relations(request: CreateRelationsRequest) -> EntityListResponse:
    """Create relations between existing entities.
    
    Examples:
        # Document system dependencies
        request = CreateRelationsRequest(
            relations=[
                Relation(
                    from_id="component/memory_service",
                    to_id="component/file_service",
                    relation_type="depends_on",
                    context="File operations for persistence"
                ),
                Relation(
                    from_id="component/file_service",
                    to_id="component/memory_service", 
                    relation_type="supports",
                    context="Provides atomic file operations"
                )
            ]
        )
        response = await create_relations(request)
        
        # Response shows both entities with new relations:
        # EntityListResponse(
        #     entities=[
        #         EntityResponse(  # memory_service
        #             relations=[
        #                 Relation(to_id="component/file_service", ...)
        #             ]
        #         ),
        #         EntityResponse(  # file_service
        #             relations=[
        #                 Relation(to_id="component/memory_service", ...)
        #             ]
        #         )
        #     ]
        # )
    """
    url = "/knowledge/relations"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool()
async def add_observations(request: AddObservationsRequest) -> EntityResponse:
    """Add observations to an existing entity.
    
    Examples:
        # Document implementation decisions with context
        request = AddObservationsRequest(
            path_id="component/search_service",
            context="Performance optimization meeting",
            observations=[
                ObservationCreate(
                    category=ObservationCategory.TECH,
                    content="Implementing FTS5 for full-text search"
                ),
                ObservationCreate(
                    category=ObservationCategory.DESIGN,
                    content="Chose FTS5 for better ranking and phrase queries"
                ),
                ObservationCreate(
                    category=ObservationCategory.FEATURE,
                    content="Added support for fuzzy matching"
                )
            ]
        )
        response = await add_observations(request)
        
        # Response shows entity with new observations:
        # EntityResponse(
        #     path_id="component/search_service",
        #     observations=[
        #         Observation(
        #             category="TECH",
        #             content="Implementing FTS5 for full-text search",
        #             context="Performance optimization meeting"
        #         ),
        #         ...
        #     ]
        # )
    """
    url = "/knowledge/observations"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())


@mcp.tool()
async def delete_observations(request: DeleteObservationsRequest) -> EntityResponse:
    """Delete specific observations from an entity.
    
    Examples:
        # Remove obsolete implementation notes
        request = DeleteObservationsRequest(
            path_id="component/indexer",
            observations=[
                "Using old indexing algorithm",
                "Temporary workaround for issue #123"
            ]
        )
        response = await delete_observations(request)
        
        # Response shows entity with observations removed:
        # EntityResponse(
        #     path_id="component/indexer",
        #     observations=[...]  # Remaining observations
        # )
    """
    url = "/knowledge/observations/delete"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())


@mcp.tool()
async def delete_relations(request: DeleteRelationsRequest) -> EntityListResponse:
    """Delete relations between entities.
    
    Examples:
        # Remove obsolete dependency
        request = DeleteRelationsRequest(
            relations=[
                Relation(
                    from_id="component/search",
                    to_id="component/old_index",
                    relation_type="depends_on"
                )
            ]
        )
        response = await delete_relations(request)
        
        # Response shows updated entities:
        # EntityListResponse(
        #     entities=[
        #         EntityResponse(  # search component
        #             relations=[...]  # Remaining relations
        #         ),
        #         EntityResponse(  # old_index component
        #             relations=[...]  # Remaining relations
        #         )
        #     ]
        # )
    """
    url = "/knowledge/relations/delete"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool()
async def delete_entities(request: DeleteEntitiesRequest) -> Dict[str, bool]:
    """Delete entities from the knowledge graph.
    
    Examples:
        # Remove obsolete components
        request = DeleteEntitiesRequest(
            path_ids=[
                "component/old_service",
                "test/obsolete_test"
            ]
        )
        response = await delete_entities(request)
        
        # Response indicates success:
        # {
        #     "deleted": true
        # }
    """
    url = "/knowledge/entities/delete"
    response = await client.post(url, json=request.model_dump())
    return response.json()