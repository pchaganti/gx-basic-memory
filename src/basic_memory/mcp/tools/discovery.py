"""Tools for discovering and analyzing knowledge graph structure."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList
from basic_memory.mcp.async_client import client



@mcp.tool(
    category="discovery",
    description="List all unique observation categories used in the knowledge base",
    examples=[
        {
            "name": "Category Usage",
            "description": "Analyze how categories are used across entity types",
            "code": """
# Get all categories
categories = await get_observation_categories()

# Get usage patterns by entity type
types = await get_entity_types()

usage_patterns = defaultdict(lambda: defaultdict(int))
for entity_type in types["types"]:
    # Get entities of this type
    entities = await list_by_type(entity_type)
    
    # Count category usage
    for entity in entities.entities:
        for obs in entity.observations:
            usage_patterns[entity_type][obs.category] += 1

# Show category usage patterns
print("Category Usage Patterns:")
for entity_type, patterns in usage_patterns.items():
    if patterns:
        print(f"\\n{entity_type}:")
        for category, count in patterns.items():
            print(f"- {category}: {count} observations")"""
        },
        {
            "name": "Knowledge Organization",
            "description": "Analyze knowledge organization patterns",
            "code": """
# Get all categories and entities
categories = await get_observation_categories()
results = await search_nodes(
    request=SearchNodesRequest(
        query="implementation architecture",
        category=None  # Search all categories
    )
)

# Analyze knowledge structure
category_content = defaultdict(list)
for entity in results.matches:
    for obs in entity.observations:
        category_content[obs.category].append({
            "entity": entity.name,
            "content": obs.content,
            "context": obs.context
        })

# Show how knowledge is organized
print("Knowledge Organization Analysis:")
for category in categories:
    content = category_content.get(category, [])
    if content:
        print(f"\\n{category.upper()} ({len(content)} items):")
        # Show example content
        examples = content[:3]
        for ex in examples:
            context = f" ({ex['context']})" if ex['context'] else ""
            print(f"- {ex['entity']}: {ex['content']}{context}")"""
        }
    ],
    output_model=List[str]
)
async def get_observation_categories() -> List[str]:
    """List all unique observation categories in use.
    
    Returns:
        List of unique category names used for observations
    """
    logger.debug("Getting all observation categories")
    url = "/discovery/observation-categories"
    response = await client.get(url)
    return ObservationCategoryList.model_validate(response.json())

