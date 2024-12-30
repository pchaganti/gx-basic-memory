"""Knowledge graph management tools for Basic Memory MCP server."""

from typing import Dict, List, Optional

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
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.mcp.tools.enhanced import enhanced_tool


@enhanced_tool(
    category="knowledge",
    examples=[{
        "name": "Create Component",
        "description": "Create a new technical component",
        "code": """
await create_entities({
    "entities": [{
        "name": "SearchService",
        "entity_type": "component",
        "description": "Full-text search capability",
        "observations": [
            "Implements FTS5 for better performance",
            "Supports fuzzy matching"
        ]
    }]
})
"""
    }]
)
async def create_entities(request: CreateEntityRequest) -> EntityListResponse:
    """Create new entities in the knowledge graph.
    
    Entities can include initial observations and properties. Entity IDs
    are automatically generated from the type and name.
    """
    url = "/knowledge/entities"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@enhanced_tool(
    category="knowledge",
    examples=[{
        "name": "Add Dependency",
        "description": "Create dependency relationship between components",
        "code": """
await create_relations({
    "relations": [{
        "from_id": "component/search_service",
        "to_id": "component/storage_service",
        "relation_type": "depends_on",
        "context": "Needs storage for search indexes"
    }]
})
"""
    }]
)
async def create_relations(request: CreateRelationsRequest) -> EntityListResponse:
    """Create relations between existing entities."""
    url = "/knowledge/relations"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@enhanced_tool(
    category="knowledge",
    examples=[{
        "name": "Get Entity Details",
        "description": "Load complete entity information",
        "code": """
# Get component details
entity = await get_entity("component/search_service")
print(f"Name: {entity.name}")
print(f"Type: {entity.entity_type}")
for obs in entity.observations:
    print(f"- {obs.content}")
"""
    }]
)
async def get_entity(path_id: PathId) -> EntityResponse:
    """Get a specific entity by its path_id."""
    try:
        url = f"/knowledge/entities/{path_id}"
        response = await client.get(url)
        if response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        response.raise_for_status()
        return EntityResponse.model_validate(response.json())
    except Exception as e:
        if hasattr(e, "response") and e.response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        raise



@enhanced_tool()
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


@enhanced_tool()
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


@enhanced_tool()
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


@enhanced_tool()
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