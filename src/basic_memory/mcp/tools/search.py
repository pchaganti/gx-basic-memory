"""Search tools for Basic Memory MCP server."""

from typing import List, Optional
from datetime import datetime, timezone
import textwrap
from collections import defaultdict

from basic_memory.mcp.server import mcp
from basic_memory.schemas.search import SearchQuery, SearchResult, SearchItemType
from basic_memory.schemas.request import OpenNodesRequest
from basic_memory.schemas.response import EntityListResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="search",
    description="Search across all content in basic-memory, including documents and entities",
    examples=[
        {
            "name": "Search with Metadata Analysis",
            "description": "Search and analyze results by metadata",
            "code": """
# Search for feature specs
results = await search(
    text="implementation", 
    types=[SearchItemType.DOCUMENT]
)

# Group by category and status
by_category = defaultdict(list)
by_status = defaultdict(list)

for r in results:
    meta = r.metadata
    if 'category' in meta:
        by_category[meta['category']].append(r)
    if 'status' in meta:
        by_status[meta['status']].append(r)

print("Results by Category:")
for category, items in by_category.items():
    print(f"\\n{category.title()}:")
    for item in items:
        print(f"- {item.path_id} (score: {item.score:.2f})")

# Find high priority items
high_priority = [
    r for r in results 
    if r.metadata.get('priority') in ['high', 'highest']
]
"""
        },
        {
            "name": "Recent Changes Analysis",
            "description": "Search and analyze recent document changes",
            "code": """
from datetime import datetime, timedelta

# Set cutoff date
cutoff = datetime.now(timezone.utc) - timedelta(days=7)

# Search for recent changes
results = await search(text="database", after_date=cutoff)

# Sort by update time
sorted_results = sorted(
    results,
    key=lambda x: x.metadata['updated_at'],
    reverse=True
)

print("Recent Changes:")
for r in sorted_results[:5]:
    print(f"\\n{r.path_id}")
    print(f"Updated: {r.metadata['updated_at']}")
    if 'author' in r.metadata:
        print(f"Author: {r.metadata['author']}")
    print(f"Score: {r.score:.2f}")
"""
        },
        {
            "name": "Entity Context Loading",
            "description": "Search for entities and load their full context",
            "code": """
# Find relevant components
results = await search(
    text="knowledge graph",
    types=[SearchItemType.ENTITY],
    entity_types=["component"]
)

if results:
    # Load full entity details
    path_ids = [r.path_id for r in results]
    context = await open_nodes(
        request=OpenNodesRequest(path_ids=path_ids)
    )

    # Analyze implementation details
    print("Implementation Components:")
    for entity in context.entities:
        print(f"\\n{entity.name}")
        
        # Show technical details
        tech_notes = [
            o.content for o in entity.observations 
            if o.category == 'tech'
        ]
        if tech_notes:
            print("Technical Notes:")
            for note in tech_notes:
                print(f"- {note}")
                
        # Show dependencies
        deps = [r for r in entity.relations if r.relation_type == 'depends_on']
        if deps:
            print("\\nDependencies:")
            for dep in deps:
                print(f"- {dep.to_id}")
"""
        }
    ]
)
async def search(
    text: str,
    types: Optional[List[SearchItemType]] = None,
    entity_types: Optional[List[str]] = None,
    after_date: Optional[datetime] = None
) -> List[SearchResult]:
    """Search across all content in basic-memory.
    
    Args:
        text: Text to search for
        types: Optional list of types to filter by (DOCUMENT, ENTITY)
        entity_types: Optional list of entity types to filter by
        after_date: Optional date to filter results after
        
    Returns:
        List of SearchResult objects sorted by relevance
    """
    query = SearchQuery(
        text=text,
        types=types,
        entity_types=entity_types,
        after_date=after_date
    )
    response = await client.post("/search/", json=query.model_dump())
    return [SearchResult.model_validate(r) for r in response.json()]


@mcp.tool(
    category="search",
    description="Load multiple entities by their path_ids in a single request",
    examples=[
        {
            "name": "Load Search Context",
            "description": "Load full entity details from search results",
            "code": """
# First search for entities
results = await search(
    text="database implementation",
    types=[SearchItemType.ENTITY]
)

# Then load full context
if results:
    path_ids = [r.path_id for r in results]
    context = await open_nodes(
        request=OpenNodesRequest(path_ids=path_ids)
    )
    
    # Group by entity type
    by_type = defaultdict(list)
    for entity in context.entities:
        by_type[entity.entity_type].append(entity)
        
    # Show breakdown
    for etype, entities in by_type.items():
        print(f"\\n{etype.title()} Components:")
        for entity in entities:
            print(f"- {entity.name}")
            if entity.observations:
                print(f"  {len(entity.observations)} observations")
            if entity.relations:
                print(f"  {len(entity.relations)} relations")
"""
        }
    ]
)
async def open_nodes(request: OpenNodesRequest) -> EntityListResponse:
    """Load multiple entities by their path_ids.
    
    Args:
        request: OpenNodesRequest containing list of path_ids to load
        
    Returns:
        EntityListResponse containing complete details for each requested entity
    """
    url = "/knowledge/nodes"
    response = await client.post(url, json=request.model_dump())
    return EntityListResponse.model_validate(response.json())