"""Search and query tools for Basic Memory MCP server."""

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import SearchNodesRequest, OpenNodesRequest
from basic_memory.schemas.response import SearchNodesResponse, EntityResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="""
    Search for entities in the knowledge graph.
    
    This is a powerful semantic search that looks across:
    - Entity names and types
    - Descriptions and metadata
    - Observation content
    - Relation contexts

    Features:
    - Case-insensitive matching
    - Partial word matches
    - Category filtering
    - Returns full entity context
    - Natural language friendly

    The search combines multiple approaches to find relevant entities,
    including text matching, category filtering, and context awareness.
    Results include complete entity information with observations
    and relations to help understand the context.
    """,
    examples=[
        {
            "name": "Basic Text Search",
            "description": "Simple search across all content",
            "code": """
# Search for SQLite-related entities
results = await search_nodes(
    request=SearchNodesRequest(query="sqlite database")
)

# Show matches with context
for entity in results.matches:
    print(f"\\n{entity.entity_type}: {entity.name}")
    print(f"Description: {entity.description}")
    print("Relevant observations:")
    for obs in entity.observations:
        print(f"- {obs.content}")
""",
        },
        {
            "name": "Category-Filtered Search",
            "description": "Find technical implementation details",
            "code": """
# Search for tech implementation details
tech_results = await search_nodes(
    request=SearchNodesRequest(
        query="async implementation",
        category="tech"  # Only tech observations
    )
)

# Show technical findings
for entity in tech_results.matches:
    tech_obs = [o for o in entity.observations 
                if o.category == "tech"]
    print(f"\\n{entity.name} - {len(tech_obs)} tech notes")
    for obs in tech_obs:
        print(f"- {obs.content}")
""",
        },
        {
            "name": "Design Decision Search",
            "description": "Find architectural decisions",
            "code": """
# Search for design decisions
design = await search_nodes(
    request=SearchNodesRequest(
        query="architecture pattern decision",
        category="design"  # Only design observations
    )
)

# Show decision history
for entity in design.matches:
    print(f"\\n{entity.name}")
    for obs in entity.observations:
        if obs.context:
            print(f"{obs.context}:")
        print(f"- {obs.content}")
""",
        },
    ],
    output_model=SearchNodesResponse,
)
async def search_nodes(request: SearchNodesRequest) -> SearchNodesResponse:
    """Search for entities in the knowledge graph."""
    url = "/knowledge/search"
    response = await client.post(url, json=request.model_dump())
    return SearchNodesResponse.model_validate(response.json())


@mcp.tool(
    description="""
    Load multiple entities by their path_ids.

    This tool efficiently loads multiple entities in a single request,
    retrieving their complete information including observations
    and relations. It's particularly useful for:
    
    - Following relation chains
    - Loading related entities
    - Batch entity retrieval
    - Context building

    The response maps each path_id to its full entity data,
    making it easy to access specific entities while maintaining
    their relationships.
    """,
    examples=[
        {
            "name": "Load Related Components",
            "description": "Load a component and its dependencies",
            "code": """
# Load component and related specs
response = await open_nodes(
    request=OpenNodesRequest(
        path_ids=[
            "component/memory_service",
            "component/file_service",
            "specification/file_format"
        ]
    )
)

# Show component relationships
for path_id, entity in response.items():
    print(f"\\n{entity.name}")
    print("Relations:")
    for rel in entity.relations:
        print(f"- {rel.relation_type} {rel.to_id}")
""",
        },
        {
            "name": "Feature Implementation Chain",
            "description": "Load feature with implementation and tests",
            "code": """
# Load entire feature chain
chain = await open_nodes(
    request=OpenNodesRequest(
        path_ids=[
            "feature/search",        # The feature
            "component/search",      # Implementation
            "test/search_test",      # Testing
            "document/search_spec"   # Documentation
        ]
    )
)

# Show implementation status
feature = chain["feature/search"]
impl = chain["component/search"]
test = chain["test/search_test"]

print(f"Feature: {feature.name}")
print(f"Implementation: {impl.description}")
print(f"Test Status: {'test' in [r.relation_type for r in test.relations]}")
""",
        },
    ],
    output_schema={
        "description": "Map of path_ids to their complete entity data",
        "type": "object",
        "additionalProperties": {
            "$ref": "#/definitions/EntityResponse",
            "description": "Full entity data including observations and relations",
        },
    },
)
async def open_nodes(request: OpenNodesRequest) -> EntityResponse:
    """Load multiple entities by their path_ids."""
    url = "/knowledge/nodes"
    response = await client.post(url, json=request.model_dump())
    return EntityResponse.model_validate(response.json())
