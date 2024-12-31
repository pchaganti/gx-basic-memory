"""Search and query tools for Basic Memory MCP server."""

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import SearchNodesRequest, OpenNodesRequest
from basic_memory.schemas.response import SearchNodesResponse, EntityListResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="Search for entities across names, descriptions, observations, and relations",
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
    description="Load multiple entities by their path_ids in a single request",
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
    output_model=EntityListResponse,
)
async def open_nodes(request: OpenNodesRequest) -> EntityListResponse:
    """Load multiple entities by their path_ids."""
    url = "/knowledge/nodes"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())
