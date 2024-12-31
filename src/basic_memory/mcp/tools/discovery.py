"""Tools for discovering and analyzing knowledge graph structure."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="""
    List all unique entity types in use across the knowledge graph.
    
    This tool helps understand the structure of your knowledge base by showing:
    - All entity types currently in use
    - Custom types you've created
    - System-defined types
    
    Useful for:
    - Understanding knowledge organization
    - Finding available entity types
    - Discovering custom types
    - Planning knowledge structure
    """,
    examples=[
        {
            "name": "List Entity Types",
            "description": "Show all entity types with counts",
            "code": """
# Get all entity types
types = await get_entity_types()

# Count entities of each type
for entity_type in types:
    entities = await list_by_type(entity_type)
    print(f"{entity_type}: {len(entities.entities)} entities")
"""
        },
        {
            "name": "Find Custom Types",
            "description": "Identify custom entity types",
            "code": """
# Get all types
types = await get_entity_types()

# Separate system and custom types
system_types = {"component", "document", "feature", "test"}
custom_types = [t for t in types if t not in system_types]

print("Custom entity types:")
for t in custom_types:
    print(f"- {t}")
"""
        }
    ],
    output_model=EntityTypeList
)
async def get_entity_types() -> List[str]:
    """List all unique entity types in use."""
    logger.debug("Getting all entity types")
    url = "/discovery/entity-types"
    response = await client.get(url)
    return EntityTypeList.model_validate(response.json())


@mcp.tool(
    description="""
    List all unique observation categories used in the knowledge graph.
    
    Categories help organize different types of observations like:
    - Technical details (tech)
    - Design decisions (design)  
    - Features (feature)
    - General notes (note)
    - Issues/bugs (issue)
    - Todo items (todo)
    
    This helps understand how knowledge is categorized and find
    specific types of information.
    """,
    examples=[
        {
            "name": "List Categories",
            "description": "Show all observation categories",
            "code": """
# Get categories
categories = await get_observation_categories()

# Group some recent entities by category
results = await search_nodes(
    request=SearchNodesRequest(
        query="database",
        category=None  # Search all categories
    )
)

# Show observations by category
for category in categories:
    obs = [o for e in results.matches 
           for o in e.observations 
           if o.category == category]
    if obs:
        print(f"\\n{category.upper()}:")
        for o in obs:
            print(f"- {o.content}")
"""
        }
    ],
    output_model=List[str] #TODO
)
async def get_observation_categories() -> List[str]:
    """List all unique observation categories in use."""
    logger.debug("Getting all observation categories")
    url = "/discovery/observation-categories"
    response = await client.get(url)
    return ObservationCategoryList.model_validate(response.json())


@mcp.tool(
    description="""
    List all entities of a specific type with optional related entities.
    
    This tool provides:
    - All entities of a given type
    - Optional related entities
    - Sorting options
    - Complete entity information
    
    Useful for:
    - Exploring entity collections
    - Finding related entities
    - Understanding entity relationships
    - Analyzing knowledge structure
    """,
    examples=[
        {
            "name": "List Components",
            "description": "Show all technical components",
            "code": """
# Get components with relations
components = await list_by_type(
    entity_type="component",
    include_related=True
)

# Show component dependencies
for entity in components.entities:
    print(f"\\n{entity.name}")
    deps = [r for r in entity.relations 
            if r.relation_type == "depends_on"]
    if deps:
        print("Dependencies:")
        for dep in deps:
            print(f"- {dep.to_id}")
"""
        },
        {
            "name": "Recent Features",
            "description": "List recently updated features",
            "code": """
# Get features sorted by update time
features = await list_by_type(
    entity_type="feature",
    sort_by="updated_at"
)

# Show recent features with status
print("Recent features:")
for entity in features.entities:
    status = next((o.content for o in entity.observations 
                  if o.category == "note"), "No status")
    print(f"- {entity.name}: {status}")
"""
        }
    ],
    output_model=TypedEntityList,
)
async def list_by_type(
    entity_type: str, 
    include_related: bool = False, 
    sort_by: Optional[str] = "updated_at"
) -> TypedEntityList:
    """List all entities of a specific type."""
    logger.debug(f"Listing entities of type: {entity_type}")
    params = {"include_related": "true" if include_related else "false"}
    if sort_by:
        params["sort_by"] = sort_by

    url = f"/discovery/entities/{entity_type}"
    response = await client.get(url, params=params)
    return TypedEntityList.model_validate(response.json())
