"""Discussion context tools for Basic Memory MCP server."""

from typing import Optional

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.schemas.memory import GraphContext, MemoryUrl


@mcp.tool(
    category="discussion",
    description="Get discussion context from a memory:// URI to continue conversations naturally.",
    examples=[
        {
            "name": "Continue Previous Discussion",
            "description": "Load context to continue a technical discussion",
            "code": """
# Get context for previous discussion about search
context = await get_discussion_context(
    url="memory://specs/search-refactor",
    depth=2, 
    timeframe="7d"
)

# Access the context components
primary = context.primary_entities    # Main discussion topic
related = context.related_entities    # Related concepts
meta = context.metadata              # Discussion metadata

# Analyze primary discussion topics
print("\\nPrimary Discussion Topic:")
for entity in primary:
    print(f"- {entity.title}")
    print(f"  Type: {entity.type}")
    if "status" in entity.metadata:
        print(f"  Status: {entity.metadata['status']}")

# Analyze related content
print("\\nRelated Topics:")
for item in related:
    print(f"- {item.title}")
    if item.relation_type:
        print(f"  Relation: {item.relation_type}")
"""
        },
        {
            "name": "Pattern Matching and Time Filtering",
            "description": "Search for matching discussions within a timeframe",
            "code": """
# Find recent discussions matching a pattern
context = await get_discussion_context(
    url="memory://design/*",     # Match all design documents
    depth=1,                     # Direct relations only
    timeframe="3d"              # Last 3 days only
)

print(f"Found {context.metadata['matched_entities']} matching discussions")
print(f"Total related items: {context.metadata['total_entities']}")

# Group by document type
by_type = {}
for entity in context.primary_entities:
    doc_type = entity.type
    if doc_type not in by_type:
        by_type[doc_type] = []
    by_type[doc_type].append(entity)

# Show summary by type
for doc_type, entities in by_type.items():
    print(f"\\n{doc_type.title()}:")
    for entity in entities:
        print(f"- {entity.title}")
        print(f"  Added: {entity.metadata.get('created_at', 'Unknown')}")
"""
        }
    ],
)
async def get_discussion_context(
    url: MemoryUrl,
    depth: Optional[int] = 2,
    timeframe: Optional[str] = "7d",
) -> GraphContext:
    """Get context needed to continue a discussion.

    This tool enables natural continuation of discussions by loading relevant context
    from memory:// URIs. It uses pattern matching to find relevant content and builds
    a rich context graph of related information.

    Args:
        url: memory:// URI pointing to discussion content (e.g. memory://specs/search)
        depth: How many relation hops to traverse (default: 2)
        timeframe: How far back to look, e.g. "7d", "24h" (default: "7d")

    Returns:
        GraphContext containing:
            - primary_entities: Directly matched content
            - related_entities: Connected content via relations
            - metadata: Context building info
    """
    # Map directly to the memory endpoint
    memory_url = MemoryUrl.validate(url)
    response = await client.get(
        f"/memory/{memory_url.relative_path()}", params={"depth": depth, "timeframe": timeframe}
    )
    return GraphContext.model_validate(response.json())