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
from basic_memory.schemas.response import EntityListResponse, EntityResponse, DeleteEntitiesResponse
from basic_memory.mcp.async_client import client
from basic_memory.services.exceptions import EntityNotFoundError


@mcp.tool(
    category="knowledge",
    description="Create new entities in the knowledge graph with names, types, and observations",
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
""",
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
""",
        },
    ],
    output_model=EntityListResponse,
)
async def create_entities(request: CreateEntityRequest) -> EntityListResponse:
    """Create new entities in the knowledge graph."""
    url = "/knowledge/entities"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool(
    category="knowledge",
    description="Create typed relationships between existing entities",
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
""",
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
""",
        },
    ],
    output_model=EntityListResponse,
)
async def create_relations(request: CreateRelationsRequest) -> EntityListResponse:
    """Create relations between existing entities."""
    url = "/knowledge/relations"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool(
    category="knowledge",
    description="Get complete information about a specific entity including observations and relations",
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
""",
        }
    ],
    output_model=EntityResponse,
)
async def get_entity(permalink: PathId, content: bool = False) -> EntityResponse:
    """Get a specific entity by its permalink.

    Args:
        permalink: Path identifier for the entity
        content: If True, includes the full markdown content of the entity
    """
    try:
        url = f"/knowledge/entities/{permalink}"
        params = {"content": "true"} if content else {}
        response = await client.get(url, params=params)
        if response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {permalink}")
        response.raise_for_status()
        return EntityResponse.model_validate(response.json())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise EntityNotFoundError(f"Entity not found: {permalink}")
        raise


@mcp.tool(
    description="Add categorized observations to an existing entity",
    examples=[
        {
            "name": "Add Implementation Notes",
            "description": "Document technical implementation details",
            "code": """
# Add technical observations
await add_observations(
    request=AddObservationsRequest(
        permalink="component/search_service",
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
""",
        }
    ],
    output_model=EntityResponse,
)
async def add_observations(request: AddObservationsRequest) -> EntityResponse:
    """Add observations to an existing entity."""
    url = "/knowledge/observations"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())


@mcp.tool(
    description="Delete specific observations from an entity while preserving other content",
    examples=[
        {
            "name": "Remove Obsolete Notes",
            "description": "Delete outdated observations",
            "code": """
# Remove old implementation notes
await delete_observations(
    request=DeleteObservationsRequest(
        permalink="component/indexer",
        observations=[
            "Using old indexing algorithm",
            "Temporary workaround for issue #123"
        ]
    )
)
""",
        }
    ],
    output_model=EntityResponse,
)
async def delete_observations(request: DeleteObservationsRequest) -> EntityResponse:
    """Delete specific observations from an entity."""
    url = "/knowledge/observations/delete"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())


@mcp.tool(
    description="Delete relationships between entities while preserving the entities themselves",
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
""",
        }
    ],
    output_model=EntityListResponse,
)
async def delete_relations(request: DeleteRelationsRequest) -> EntityListResponse:
    """Delete relations between entities."""
    url = "/knowledge/relations/delete"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())


@mcp.tool(
    description="Permanently delete entities and all related content (observations and relations)",
    examples=[
        {
            "name": "Remove Old Components",
            "description": "Delete obsolete components",
            "code": """
# Remove deprecated components
await delete_entities(
    request=DeleteEntitiesRequest(
        permalinks=[
            "component/old_service",
            "test/obsolete_test"
        ]
    )
)
""",
        }
    ],
    output_model=Dict[str, bool],
)
async def delete_entities(request: DeleteEntitiesRequest) -> DeleteEntitiesResponse:
    """Delete entities from the knowledge graph."""
    url = "/knowledge/entities/delete"
    response = await client.post(url, json=request.model_dump())
    return DeleteEntitiesResponse.model_validate(response.json())
