"""Search and query tools for Basic Memory MCP server."""

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import SearchNodesRequest, OpenNodesRequest
from basic_memory.schemas.response import SearchNodesResponse, EntityListResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="search",
    description="Search for entities across names, descriptions, observations, and relations",
    examples=[
        {
            "name": "Technical Search",
            "description": "Find implementation details and patterns",
            "code": """
# Search for database-related components
results = await search_nodes(
    request=SearchNodesRequest(
        query="sqlite database implementation",
        category="tech"  # Focus on technical details
    )
)

# Analyze implementation patterns
for entity in results.matches:
    print(f"\\n{entity.name} Implementation:")
    
    # Technical details
    tech_notes = [o.content for o in entity.observations 
                 if o.category == "tech"]
    if tech_notes:
        print("Technical Notes:")
        for note in tech_notes:
            print(f"- {note}")
    
    # Dependencies
    deps = [r for r in entity.relations 
            if r.relation_type == "depends_on"]
    if deps:
        print("\\nDependencies:")
        for dep in deps:
            print(f"- {dep.to_id}")"""
        },
        {
            "name": "Feature Context",
            "description": "Build complete feature implementation context",
            "code": """
# Start with feature search
feature_results = await search_nodes(
    request=SearchNodesRequest(
        query="semantic search feature"
    )
)

# Collect related entities for context
related_ids = set()
for entity in feature_results.matches:
    # Add feature itself
    related_ids.add(entity.path_id)
    # Add related entities
    for relation in entity.relations:
        related_ids.add(relation.to_id)

# Load complete context
if related_ids:
    context = await open_nodes(
        request=OpenNodesRequest(
            path_ids=list(related_ids)
        )
    )
    
    # Analyze implementation status
    components = [e for e in context.entities 
                 if e.entity_type == "component"]
    tests = [e for e in context.entities 
             if e.entity_type == "test"]
    specs = [e for e in context.entities 
             if e.entity_type == "specification"]
            
    print("Implementation Status:")
    print(f"- Components: {len(components)}")
    print(f"- Tests: {len(tests)}")
    print(f"- Specs: {len(specs)}")"""
        },
        {
            "name": "Design Analysis",
            "description": "Extract architectural decisions and patterns",
            "code": """
# Search for design decisions
design_results = await search_nodes(
    request=SearchNodesRequest(
        query="architecture pattern",
        category="design"
    )
)

# Group decisions by component
from collections import defaultdict
decisions = defaultdict(list)

for entity in design_results.matches:
    # Extract design observations
    design_notes = [o for o in entity.observations 
                   if o.category == "design"]
    if design_notes:
        decisions[entity.name].extend(design_notes)

# Show architectural decisions
for component, notes in decisions.items():
    print(f"\\n{component} Architecture:")
    for note in notes:
        context = note.context or "Design Decision"
        print(f"\\n{context}:")
        print(f"- {note.content}")"""
        },
        {
            "name": "Knowledge Chain",
            "description": "Follow knowledge links to build deep context",
            "code": """
# Start with initial concept
initial = await search_nodes(
    request=SearchNodesRequest(query="semantic web")
)

# Build knowledge chain
seen_ids = set()
to_explore = set()

# Add initial matches
for entity in initial.matches:
    seen_ids.add(entity.path_id)
    for relation in entity.relations:
        to_explore.add(relation.to_id)

# Explore up to 2 levels deep
knowledge_chain = initial.matches
for _ in range(2):
    if not to_explore:
        break
        
    # Load next level
    next_ids = list(to_explore - seen_ids)
    if next_ids:
        next_level = await open_nodes(
            request=OpenNodesRequest(path_ids=next_ids)
        )
        
        # Update tracking
        knowledge_chain.extend(next_level.entities)
        seen_ids.update(next_ids)
        to_explore.clear()
        
        # Add new relations
        for entity in next_level.entities:
            for relation in entity.relations:
                to_explore.add(relation.to_id)

# Analyze knowledge structure
print(f"Knowledge chain depth: {len(seen_ids)} entities")
type_counts = defaultdict(int)
for entity in knowledge_chain:
    type_counts[entity.entity_type] += 1

print("\\nKnowledge composition:")
for type_, count in type_counts.items():
    print(f"- {type_}: {count} entities")"""
        }
    ],
    output_model=SearchNodesResponse,
)
async def search_nodes(request: SearchNodesRequest) -> SearchNodesResponse:
    """Search for entities in the knowledge graph.
    
    Args:
        request: Search parameters including query text and optional category
        
    Returns:
        SearchNodesResponse containing matching entities and search metadata
    """
    url = "/knowledge/search"
    response = await client.post(url, json=request.model_dump())
    return SearchNodesResponse.model_validate(response.json())


@mcp.tool(
    category="search",
    description="Load multiple entities by their path_ids in a single request",
    examples=[
        {
            "name": "Implementation Chain",
            "description": "Load and analyze implementation dependencies",
            "code": """
# Load feature implementation chain
chain = await open_nodes(
    request=OpenNodesRequest(
        path_ids=[
            "feature/semantic_search",    # The feature
            "component/search_service",   # Core implementation
            "component/index_service",    # Supporting service
            "test/search_integration",    # Integration tests
            "document/search_spec"        # Documentation
        ]
    )
)

def analyze_dependencies(entities):
    deps = defaultdict(list)
    for entity in entities:
        # Direct dependencies
        direct = [r.to_id for r in entity.relations 
                 if r.relation_type == "depends_on"]
        deps[entity.path_id].extend(direct)
        
        # Implicit dependencies via observations
        for obs in entity.observations:
            if "requires" in obs.content.lower():
                deps[entity.path_id].append(
                    f"Implicit: {obs.content}"
                )
    return deps

# Show implementation structure
deps = analyze_dependencies(chain.entities)
for path_id, dependencies in deps.items():
    print(f"\\n{path_id} dependencies:")
    for dep in dependencies:
        print(f"- {dep}")"""
        },
        {
            "name": "Technical Analysis",
            "description": "Deep dive into technical implementation",
            "code": """
# First find technical components
tech_results = await search_nodes(
    request=SearchNodesRequest(
        query="search implementation",
        category="tech"
    )
)

# Load full technical context
tech_ids = [e.path_id for e in tech_results.matches 
            if e.entity_type == "component"]

if tech_ids:
    details = await open_nodes(
        request=OpenNodesRequest(path_ids=tech_ids)
    )
    
    # Analyze technical architecture
    print("Technical Architecture:\\n")
    
    for entity in details.entities:
        print(f"{entity.name}:")
        
        # Core capabilities
        tech_notes = [o.content for o in entity.observations 
                     if o.category == "tech"]
        if tech_notes:
            print("\\nCapabilities:")
            for note in tech_notes:
                print(f"- {note}")
        
        # Design decisions
        design_notes = [o.content for o in entity.observations 
                       if o.category == "design"]
        if design_notes:
            print("\\nDesign Decisions:")
            for note in design_notes:
                print(f"- {note}")
        
        # Dependencies
        deps = [r for r in entity.relations 
               if r.relation_type == "depends_on"]
        if deps:
            print("\\nDependencies:")
            for dep in deps:
                print(f"- {dep.to_id}")
                
        print("\\n---")"""
        }
    ],
    output_model=EntityListResponse,
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