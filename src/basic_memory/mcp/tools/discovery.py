"""Tools for discovering and analyzing knowledge graph structure."""

from typing import List, Optional

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="discovery",
    description="List all unique entity types in the knowledge graph",
    examples=[
        {
            "name": "Type Analysis",
            "description": "Analyze entity type distribution and patterns",
            "code": """
# Get all entity types
types = await get_entity_types()

# Analyze distribution by type
type_stats = {}
for entity_type in types["types"]:
    entities = await list_by_type(
        entity_type=entity_type,
        include_related=True
    )
    type_stats[entity_type] = {
        "count": len(entities.entities),
        "with_observations": sum(1 for e in entities.entities 
                               if e.observations),
        "with_relations": sum(1 for e in entities.entities 
                            if e.relations)
    }

# Show type analysis
print("Knowledge Graph Structure:")
for type_, stats in type_stats.items():
    print(f"\\n{type_}:")
    print(f"- Total: {stats['count']} entities")
    print(f"- With observations: {stats['with_observations']}")
    print(f"- With relations: {stats['with_relations']}")"""
        },
        {
            "name": "Custom Type Detection",
            "description": "Identify and analyze custom entity types",
            "code": """
# Get all types
types = await get_entity_types()

# Separate system and custom types
system_types = {
    "component", "document", "feature", 
    "test", "concept"
}
custom_types = [t for t in types["types"] 
                if t not in system_types]

if custom_types:
    print("Custom entity types discovered:")
    for type_ in custom_types:
        # Get entities of this type
        entities = await list_by_type(type_)
        
        print(f"\\n{type_} ({len(entities.entities)} entities):")
        
        # Analyze type characteristics
        observations = [o for e in entities.entities 
                       for o in e.observations]
        categories = {o.category for o in observations}
        relations = [r for e in entities.entities 
                    for r in e.relations]
        relation_types = {r.relation_type for r in relations}
        
        if categories:
            print("Used categories:")
            for cat in sorted(categories):
                print(f"- {cat}")
                
        if relation_types:
            print("\\nRelation types:")
            for rt in sorted(relation_types):
                print(f"- {rt}")"""
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


@mcp.tool(
    category="discovery",
    description="List all entities of a specific type",
    examples=[
        {
            "name": "Component Analysis",
            "description": "Analyze component implementation patterns",
            "code": """
# Get all components with relations
components = await list_by_type(
    entity_type="component",
    include_related=True
)

# Analyze implementation patterns
dependency_patterns = defaultdict(list)
implementation_patterns = defaultdict(list)

for entity in components.entities:
    # Analyze dependencies
    deps = [r for r in entity.relations 
            if r.relation_type == "depends_on"]
    if deps:
        pattern = f"{len(deps)} dependencies"
        dependency_patterns[pattern].append(entity.name)
    
    # Analyze implementation details
    tech_obs = [o for o in entity.observations 
                if o.category == "tech"]
    if tech_obs:
        pattern = f"{len(tech_obs)} technical notes"
        implementation_patterns[pattern].append(entity.name)

print("Component Implementation Patterns:\\n")
print("Dependency Patterns:")
for pattern, components in dependency_patterns.items():
    print(f"\\n{pattern}:")
    for comp in components:
        print(f"- {comp}")

print("\\nImplementation Detail Patterns:")
for pattern, components in implementation_patterns.items():
    print(f"\\n{pattern}:")
    for comp in components:
        print(f"- {comp}")"""
        },
        {
            "name": "Feature Coverage",
            "description": "Analyze feature implementation status",
            "code": """
# Get all features
features = await list_by_type(
    entity_type="feature",
    include_related=True,
    sort_by="updated_at"
)

def analyze_feature_status(feature):
    # Check implementation
    has_component = any(
        r.relation_type == "implemented_by" 
        for r in feature.relations
    )
    
    # Check testing
    has_tests = any(
        r.to_id.startswith("test/") 
        for r in feature.relations
    )
    
    # Check documentation
    has_docs = any(
        r.to_id.startswith("document/") 
        for r in feature.relations
    )
    
    # Get latest status note
    status_notes = [o for o in feature.observations 
                   if o.category == "note"]
    latest_status = status_notes[-1].content if status_notes else None
    
    return {
        "implemented": has_component,
        "tested": has_tests,
        "documented": has_docs,
        "status": latest_status
    }

# Show feature coverage
print("Feature Implementation Status:\\n")
for feature in features.entities:
    status = analyze_feature_status(feature)
    
    print(f"{feature.name}:")
    print(f"- Implementation: {'✓' if status['implemented'] else '⨯'}")
    print(f"- Tests: {'✓' if status['tested'] else '⨯'}")
    print(f"- Documentation: {'✓' if status['documented'] else '⨯'}")
    if status['status']:
        print(f"- Status: {status['status']}")
    print()"""
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
        sort_by: Field to sort results by
        
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