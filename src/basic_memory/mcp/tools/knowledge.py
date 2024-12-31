"""Knowledge graph management tools for Basic Memory MCP server."""

from typing import Dict

import httpx

from basic_memory.mcp.server import mcp
from basic_memory.schemas.base import PathId
from basic_memory.schemas.request import (
    CreateEntityRequest,
    CreateRelationsRequest,
    AddObservationsRequest,
)
from basic_memory.schemas.delete import (
    DeleteEntitiesRequest,
    DeleteObservationsRequest,
    DeleteRelationsRequest,
)
from basic_memory.schemas.response import EntityListResponse, EntityResponse
from basic_memory.mcp.async_client import client
from basic_memory.services.exceptions import EntityNotFoundError


@mcp.tool(
    category="knowledge",
    description="""
    Create new entities in the knowledge graph.

    Entities are the core building blocks of the knowledge graph. Each entity:
    - Has a unique name and type
    - Can have multiple observations
    - Can have relations to other entities
    - Maintains creation/update timestamps
    - Supports optional descriptions

    Entity types help organize knowledge and enable patterns like:
    - Components for technical implementations
    - Features for user-facing capabilities 
    - Concepts for abstract ideas
    - Decisions for architectural choices
    - Documents for detailed writeups
    """,
    examples=[
        {
            "name": "Create Component",
            "description": "Create a new technical component",
            "code": """
# Create search service component
await create_entities({
    "entities": [{
        "name": "SearchService",
        "entity_type": "component",
        "description": "Full-text search capability",
        "observations": [
            "Implements FTS5 for better performance",
            "Supports fuzzy matching",
            "Handles multiple indexes"
        ]
    }]
})
"""
        },
        {
            "name": "Create Feature",
            "description": "Document a user-facing feature",
            "code": """
# Create feature with implementation notes
await create_entities({
    "entities": [{
        "name": "SemanticSearch",
        "entity_type": "feature",
        "description": "Natural language search across knowledge base",
        "observations": [
            "Uses embeddings for matching",
            "Supports fuzzy queries",
            "Ranks results by relevance"
        ]
    }]
})
"""
        }
    ]
)
async def create_entities(request: CreateEntityRequest) -> EntityListResponse:
    """Create new entities in the knowledge graph."""
    url = "/knowledge/entities"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool(
    category="knowledge",
    description="""
    Create relations between existing entities.

    Relations form the edges of the knowledge graph, connecting entities with:
    - Directional relationships (from_id -> to_id)
    - Typed connections (implements, depends_on, etc.)
    - Optional context notes
    - Automatic timestamp tracking

    Common relation patterns:
    - Component implements Feature
    - Component depends_on Component
    - Test validates Component
    - Document describes Feature
    """,
    examples=[
        {
            "name": "Add Dependency",
            "description": "Create dependency relationship between components",
            "code": """
# Document component dependency
await create_relations({
    "relations": [{
        "from_id": "component/search_service",
        "to_id": "component/storage_service",
        "relation_type": "depends_on",
        "context": "Needs storage for search indexes"
    }]
})
"""
        },
        {
            "name": "Link Implementation",
            "description": "Connect implementation to feature",
            "code": """
# Link component to feature
await create_relations({
    "relations": [{
        "from_id": "component/search_service",
        "to_id": "feature/semantic_search",
        "relation_type": "implements",
        "context": "Primary search implementation"
    }]
})
"""
        }
    ]
)
async def create_relations(request: CreateRelationsRequest) -> EntityListResponse:
    """Create relations between existing entities."""
    url = "/knowledge/relations"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool(
    category="knowledge",
    description="""
    Get complete information about a specific entity.

    Returns the full entity context including:
    - Basic entity details (name, type, description)
    - All observations with categories
    - All relations (both incoming and outgoing)
    - Timestamps and metadata

    Useful for:
    - Understanding entity details
    - Following relationships
    - Finding related knowledge
    - Analyzing implementation patterns
    """,
    examples=[
        {
            "name": "View Component Details",
            "description": "Get complete component information",
            "code": """
# Get component implementation details
component = await get_entity("component/search_service")

# Show technical details
tech_notes = [obs for obs in component.observations 
              if obs.category == "tech"]
print(f"{component.name} Implementation:")
for note in tech_notes:
    print(f"- {note.content}")

# Show dependencies
deps = [rel for rel in component.relations 
        if rel.relation_type == "depends_on"]
print("\\nDependencies:")
for dep in deps:
    print(f"- {dep.to_id}")
"""
        }
    ]
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
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        raise


@mcp.tool(
    description="""
    Add new observations to an existing entity.

    Observations capture atomic pieces of knowledge about an entity:
    - Technical details
    - Design decisions
    - Feature specifications
    - Implementation notes
    - Issues or concerns
    - Todo items

    Each observation has:
    - A category for organization
    - Content describing the observation
    - Optional context for additional detail
    - Automatic timestamp tracking
    """,
    examples=[
        {
            "name": "Add Implementation Notes",
            "description": "Document technical implementation details",
            "code": """
# Add technical observations
await add_observations(
    request=AddObservationsRequest(
        path_id="component/search_service",
        context="Performance optimization",
        observations=[
            ObservationCreate(
                category="tech",
                content="Implemented FTS5 for better search"
            ),
            ObservationCreate(
                category="tech",
                content="Added result caching"
            ),
            ObservationCreate(
                category="design",
                content="Chose FTS5 for better ranking"
            )
        ]
    )
)
"""
        }
    ]
)
async def add_observations(request: AddObservationsRequest) -> EntityResponse:
    """Add observations to an existing entity."""
    url = "/knowledge/observations"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())


@mcp.tool(
    description="""
    Delete specific observations from an entity.

    This tool:
    - Removes selected observations
    - Maintains entity history
    - Updates timestamps
    - Preserves relations
    
    Observations must match exactly for deletion.
    The operation is selective - only specified
    observations are removed.
    """,
    examples=[
        {
            "name": "Remove Obsolete Notes",
            "description": "Delete outdated observations",
            "code": """
# Remove old implementation notes
await delete_observations(
    request=DeleteObservationsRequest(
        path_id="component/indexer",
        observations=[
            "Using old indexing algorithm",
            "Temporary workaround for issue #123"
        ]
    )
)
"""
        }
    ]
)
async def delete_observations(request: DeleteObservationsRequest) -> EntityResponse:
    """Delete specific observations from an entity."""
    url = "/knowledge/observations/delete"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())


@mcp.tool(
    description="""
    Delete relations between entities.

    This tool:
    - Removes specific relationships
    - Updates both source and target entities
    - Maintains entity history
    - Preserves observations
    
    Relations must match exactly (from_id, to_id, and type)
    for deletion. The operation only affects the specified
    relations, leaving other connections intact.
    """,
    examples=[
        {
            "name": "Remove Dependency",
            "description": "Delete an obsolete dependency",
            "code": """
# Remove old dependency
await delete_relations(
    request=DeleteRelationsRequest(
        relations=[{
            "from_id": "component/search",
            "to_id": "component/old_index",
            "relation_type": "depends_on"
        }]
    )
)
"""
        }
    ]
)
async def delete_relations(request: DeleteRelationsRequest) -> EntityListResponse:
    """Delete relations between entities."""
    url = "/knowledge/relations/delete"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool(
    description="""
    Delete entities from the knowledge graph.

    This operation:
    1. Removes the entity completely
    2. Deletes all its observations
    3. Removes all relations (both ways)
    4. Updates related indexes
    
    This is a permanent operation that cannot be
    undone through the API. Use with caution.
    """,
    examples=[
        {
            "name": "Remove Old Components",
            "description": "Delete obsolete components",
            "code": """
# Remove deprecated components
await delete_entities(
    request=DeleteEntitiesRequest(
        path_ids=[
            "component/old_service",
            "test/obsolete_test"
        ]
    )
)
"""
        }
    ]
)
async def delete_entities(request: DeleteEntitiesRequest) -> Dict[str, bool]:
    """Delete entities from the knowledge graph."""
    url = "/knowledge/entities/delete"
    response = await client.post(url, json=request.model_dump())
    if response.status_code == 204:
        return {"deleted": True}
    return response.json()
