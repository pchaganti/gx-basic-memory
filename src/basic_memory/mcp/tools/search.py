"""Search tools for Basic Memory MCP server."""

from basic_memory.mcp.server import mcp
from basic_memory.schemas.search import SearchQuery, SearchResponse
from basic_memory.schemas.request import OpenNodesRequest
from basic_memory.schemas.response import EntityListResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="search",
    description="Search across all content in basic-memory, including documents and entities",
    examples=[
        {
            "name": "Basic Full-text Search with Analysis",
            "description": "Search and analyze results by metadata categories",
            "code": """
# Full text search
results = await search(
    query=SearchQuery(
        text="implementation"  # Full text query
    )
)

# Group by status and type
by_status = defaultdict(list)
by_type = defaultdict(list)

for result in results.results:
    meta = result.metadata
    path = result.permalink
    
    # Group by status if available
    if "status" in meta:
        by_status[meta["status"]].append(path)
        
    # Always group by type
    by_type[result.type].append(path)

print("\\nBy Status:")
for status, paths in by_status.items():
    print(f"\\n{status.title()}:")
    for path in paths:
        print(f"- {path}")

print("\\nBy Type:")
for type_, paths in by_type.items():
    print(f"\\n{type_.title()}:")
    for path in paths:
        print(f"- {path}")
""",
        },
        {
            "name": "Recent Changes in Entity Types",
            "description": "Find recent changes in specific entity types",
            "code": """
from datetime import datetime, timezone, timedelta

# Set search parameters
cutoff = datetime.now(timezone.utc) - timedelta(days=7)
entity_types = ["component", "specification"]

# Search for recent changes
results = await search(
    query=SearchQuery(
        text="*",  # Match all
        entity_types=entity_types,
        after_date=cutoff.isoformat()
    )
)

# Sort by update time
sorted_results = sorted(
    results.results,
    key=lambda x: x.metadata.get("updated_at", ""),
    reverse=True
)

print("Recent Changes:")
for result in sorted_results:
    print(f"\\n{result.permalink}")
    print(f"Type: {result.type}")
    print(f"Score: {result.score:.2f}")
    if "updated_at" in result.metadata:
        print(f"Updated: {result.metadata['updated_at']}")
""",
        },
        {
            "name": "Technical Documentation Search",
            "description": "Search technical documentation with smart filtering",
            "code": """
# Search technical documentation
results = await search(
    query=SearchQuery(
        text="database implementation",
        types=["document"]  # Only documents
    )
)

# Filter and process results
docs = []
for result in results.results:
    meta = result.metadata
    
    # Include if it's a technical document
    if (meta.get("category") in ["specification", "technical"] or
        any(tag in meta.get("tags", []) for tag in ["technical", "spec", "documentation"])):
        docs.append(result)

# Sort by relevance score
docs.sort(key=lambda x: x.score)

print("Technical Documentation:")
for doc in docs:
    print(f"\\n{doc.permalink}")
    if "title" in doc.metadata:
        print(f"Title: {doc.metadata['title']}")
    print(f"Score: {doc.score:.2f}")
    if "tags" in doc.metadata:
        print(f"Tags: {', '.join(doc.metadata['tags'])}")
""",
        },
        {
            "name": "Related Content Search",
            "description": "Find content related to a specific entity",
            "code": """
# First get the entity to extract key terms
entity = await get_entity(permalink="component/memory_service")

if entity:
    # Build search terms from entity info
    search_terms = [
        entity.get("name", ""),
        *entity.get("tags", []),
        entity.get("entity_type", "")
    ]
    
    # Search using combined terms
    results = await search(
        query=SearchQuery(
            text=" ".join(filter(None, search_terms))
        )
    )
    
    # Filter out the original entity and sort by relevance
    related = [r for r in results.results if r.permalink != entity["permalink"]]
    related.sort(key=lambda x: x.score)

    print(f"Content Related to {entity['name']}:")
    for result in related[:5]:  # Top 5 most relevant
        print(f"\\n{result.permalink}")
        print(f"Type: {result.type}")
        print(f"Score: {result.score:.2f}")
""",
        },
    ],
)
async def search(query: SearchQuery) -> SearchResponse:
    """Search across all content in basic-memory.

    Args:
        query: SearchQuery object with search parameters including:
            - text: Search text (required)
            - types: Optional list of content types to search ("document" or "entity")
            - entity_types: Optional list of entity types to filter by
            - after_date: Optional date filter for recent content

    Returns:
        SearchResponse with search results and metadata
    """
    response = await client.post("/search/", json=query.model_dump())
    return SearchResponse.model_validate(response.json())


@mcp.tool(
    category="search",
    description="Load multiple entities by their permalinks in a single request",
    examples=[
        {
            "name": "Load and Analyze Entity Context",
            "description": "Load full entity details and analyze relationships",
            "code": """
# First search for related entities
results = await search(
    query=SearchQuery(
        text="knowledge graph",
        types=["entity"],
        entity_types=["component", "concept"]
    )
)

if results.results:
    # Load full context for found entities
    permalinks = [r.permalink for r in results.results]
    context = await open_nodes(
        request=OpenNodesRequest(permalinks=permalinks)
    )
    
    # Analyze relationships
    relationship_map = defaultdict(list)
    for entity in context.entities:
        print(f"\\n{entity.name} ({entity.entity_type})")
        
        # Group by relationship type
        for relation in entity.relations:
            relationship_map[relation.relation_type].append(
                (entity.name, relation.to_id)
            )
    
    # Show relationship summary
    print("\\nRelationship Summary:")
    for rel_type, connections in relationship_map.items():
        print(f"\\n{rel_type}:")
        for source, target in connections:
            print(f"- {source} -> {target}")
""",
        }
    ],
)
async def open_nodes(request: OpenNodesRequest) -> EntityListResponse:
    """Load multiple entities by their permalinks.

    Args:
        request: OpenNodesRequest containing list of permalinks to load

    Returns:
        EntityListResponse containing complete details for each requested entity
    """
    url = "/knowledge/nodes"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())
