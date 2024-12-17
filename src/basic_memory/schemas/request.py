"""Request schemas for interacting with the knowledge graph.

This module defines all the request schemas for creating, retrieving, and managing
knowledge graph entities. Each schema includes validation rules and clear examples
of proper usage.

Request Types:
1. Entity Creation - Create new nodes in the graph
2. Observation Addition - Add facts to existing entities
3. Relation Creation - Connect entities with typed edges
4. Node Search - Find entities across the graph
5. Node Retrieval - Load specific entities by ID
"""

from typing import List, Optional, Annotated

from annotated_types import MinLen, MaxLen
from pydantic import BaseModel

from basic_memory.schemas.base import EntityId, Observation, Entity, Relation


class AddObservationsRequest(BaseModel):
    """Add new observations to an existing entity.

    Observations are atomic pieces of information about the entity.
    Each observation should be a single fact or note that adds value
    to our understanding of the entity.

    Example Requests:

    1. Adding implementation details:
    {
        "entity_id": "component/memory_service",
        "observations": [
            "Added support for async operations",
            "Improved error handling with custom exceptions",
            "Now uses SQLAlchemy 2.0 features"
        ]
    }

    2. Documenting a decision:
    {
        "entity_id": "decision/db_schema_design",
        "observations": [
            "Chose SQLite for local-first storage",
            "Added support for full-text search via FTS5",
            "Implemented proper foreign key constraints"
        ],
        "context": "Initial database design meeting"
    }

    Best Practices:
    1. Keep observations atomic - one clear fact per observation
    2. Use complete, well-formed sentences
    3. Include relevant context in the observation text
    4. Add observations in logical groups for better history tracking
    """

    entity_id: EntityId
    context: Optional[str] = None
    observations: List[Observation]


class CreateEntityRequest(BaseModel):
    """Create one or more new entities in the knowledge graph.

    Entities represent nodes in the knowledge graph. They can be created
    with initial observations and optional descriptions. Entity IDs are
    automatically generated from the type and name.

    Example Request:
    {
        "entities": [
            {
                "name": "SearchService",
                "entity_type": "component",
                "description": "Handles knowledge graph querying",
                "observations": [
                    "Implements full-text search",
                    "Uses SQLite FTS5 extension",
                    "Supports both exact and fuzzy matching"
                ]
            },
            {
                "name": "API_Documentation",
                "entity_type": "document",
                "description": "Basic Memory API Reference",
                "observations": [
                    "Documents REST endpoints",
                    "Includes OpenAPI schema",
                    "Provides usage examples"
                ]
            }
        ]
    }

    Best Practices:
    1. Choose clear, descriptive names
    2. Use appropriate entity types (see base.py for common types)
    3. Include meaningful descriptions
    4. Add relevant initial observations
    5. Consider creating relations after entity creation
    """

    entities: Annotated[List[Entity], MinLen(1)]


class SearchNodesRequest(BaseModel):
    """Search for entities in the knowledge graph.

    The search looks across multiple fields:
    - Entity names
    - Entity types
    - Descriptions 
    - Observations

    Features:
    - Case-insensitive matching
    - Partial word matches
    - Returns full entity objects with relations
    - Includes all matching entities

    Example Queries:
    - "memory" - Find entities related to memory systems
    - "SQLite" - Find database-related components
    - "test" - Find test-related entities
    - "implementation" - Find concrete implementations
    - "service" - Find service components

    Note: Currently uses SQL ILIKE for matching. Wildcard (*) searches
    and full-text search capabilities are planned for future versions.

    Best Practice: Use specific, meaningful terms that would appear
    in the target entities' content.
    """

    query: Annotated[str, MinLen(1), MaxLen(200)]


class OpenNodesRequest(BaseModel):
    """Retrieve specific entities by their IDs.

    Used to load complete entity details including all observations
    and relations. Particularly useful for following relations
    discovered through search.

    Example Request:
    {
        "entity_ids": [
            "component/memory_service",
            "document/api_spec",
            "test/memory_service_test"
        ]
    }

    Important Notes:
    1. IDs must include the entity type prefix
    2. Non-existent IDs are silently skipped
    3. Returns complete entity objects
    4. Relations are included in response
    
    Best Practice: Use this to explore the graph by following
    relations between entities that interest you.
    """

    entity_ids: Annotated[List[EntityId], MinLen(1)]


class CreateRelationsRequest(BaseModel):
    """Create new relations between existing entities.

    Relations are directed edges that connect entities in meaningful ways.
    They use active voice verbs to describe the relationship from the
    source entity to the target entity.

    Example Request:
    {
        "relations": [
            {
                "from_id": "test/memory_service_test",
                "to_id": "component/memory_service",
                "relation_type": "validates",
                "context": "Comprehensive test suite for core functionality"
            },
            {
                "from_id": "person/alice",
                "to_id": "document/architecture_spec",
                "relation_type": "authored",
                "context": "Initial system design"
            },
            {
                "from_id": "component/memory_service",
                "to_id": "component/database_service",
                "relation_type": "depends_on",
                "context": "Requires database service for persistence"
            }
        ]
    }

    Best Practices:
    1. Use established relation_types when possible (see base.py)
    2. Consider the direction carefully - relations are one-way
    3. Add context when the relationship needs explanation
    4. Create reciprocal relations if needed (e.g., A depends_on B, B supports A)
    5. Verify both entities exist before creating relations
    6. Use relations to build a rich, navigable knowledge graph
    """

    relations: List[Relation]