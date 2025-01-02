"""Tools for discovering and analyzing knowledge graph structure."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="discovery",
    description="""List all unique entity types in use across the knowledge graph.
    
    This tool helps understand knowledge organization by:
    - Discovering available entity types
    - Understanding knowledge graph structure
    - Identifying custom entity types
    - Analyzing knowledge organization patterns
    
    Essential for AI tools to:
    - Navigate knowledge hierarchy
    - Understand domain modeling
    - Identify specialized entity types
    - Plan knowledge organization
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
    """List all unique entity types in use.
    
    Returns:
        List of unique entity type names used in the knowledge graph
    """
    logger.debug("Getting all entity types")
    url = "/discovery/entity-types"
    response = await client.get(url)
    return EntityTypeList.model_validate(response.json())


@mcp.tool(
    category="discovery",
    description="""List all unique observation categories used for organizing information.
    
    This tool helps understand knowledge classification by:
    - Revealing knowledge categorization schemes
    - Understanding observation types
    - Discovering knowledge patterns
    - Identifying domain-specific categories
    
    Valuable for AI tools to:
    - Organize new observations correctly
    - Filter and find relevant information
    - Maintain consistent categorization
    - Understand knowledge structure
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


@mcp.tool(
    category="discovery",
    description="""List all entities of a specific type with optional sorting and relations.
    
    This tool enables systematic knowledge exploration by:
    - Retrieving all entities of a given type
    - Including relationship information
    - Sorting by various criteria
    - Building comprehensive type-specific views
    
    Particularly useful for AI tools to:
    - Analyze implementation patterns
    - Track feature status
    - Understand component relationships
    - Build type-specific context
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
    """List all entities of a specific type.
    
    Args:
        entity_type: Type of entities to retrieve
        include_related: Whether to include related entities
        sort_by: Field to sort results by, defaults to 'updated_at'
        
    Returns:
        TypedEntityList containing matching entities and metadata
    """
    logger.debug(f"Listing entities of type: {entity_type}")
    params = {"include_related": "true" if include_related else "false"}
    if sort_by:
        params["sort_by"] = sort_by

    url = f"/discovery/entities/{entity_type}"
    response = await client.get(url, params=params)
    return TypedEntityList.model_validate(response.json())