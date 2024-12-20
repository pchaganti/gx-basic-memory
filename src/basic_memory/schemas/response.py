"""Response schemas for knowledge graph operations.

This module defines the response formats for all knowledge graph operations.
Each response includes complete information about the affected entities,
including IDs that can be used in subsequent operations.

Key Features:
1. Every created/updated object gets an ID
2. Relations are included with their parent entities
3. Responses include everything needed for next operations
4. Bulk operations return all affected items
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from basic_memory.schemas.base import Observation, EntityId, Relation


class SQLAlchemyModel(BaseModel):
    """Base class for models that read from SQLAlchemy attributes.

    This base class handles conversion of SQLAlchemy model attributes
    to Pydantic model fields. All response models extend this to ensure
    proper handling of database results.
    """

    model_config = ConfigDict(from_attributes=True)


class ObservationResponse(SQLAlchemyModel):
    """Schema for observation data returned from the service.

    Each observation gets a unique ID that can be used for later
    reference or deletion.

    Example Response:
    {
        "id": 123,
        "content": "Implements SQLite storage for persistence"
    }
    """

    id: int
    content: Observation


class ObservationsResponse(SQLAlchemyModel):
    """Response schema for bulk observation operations.

    Returns all added/affected observations with their IDs and
    the entity they were added to.

    Example Response:
    {
        "entity_id": "component/memory_service",
        "observations": [
            {
                "id": 123,
                "content": "Added async support"
            },
            {
                "id": 124,
                "content": "Improved error handling"
            }
        ]
    }
    """

    entity_id: EntityId
    observations: List[ObservationResponse]


class RelationResponse(Relation, SQLAlchemyModel):
    """Response schema for relation operations.

    Extends the base Relation model with a unique ID that can be
    used for later modification or deletion.

    Example Response:
    {
        "id": 45,
        "from_id": "test/memory_test",
        "to_id": "component/memory_service",
        "relation_type": "validates",
        "context": "Comprehensive test suite"
    }
    """

    id: int


class EntityResponse(SQLAlchemyModel):
    """Complete entity data returned from the service.

    This is the most comprehensive entity view, including:
    1. Basic entity details (id, name, type)
    2. All observations with their IDs
    3. All relations with their IDs
    4. Optional description

    Example Response:
    {
        "id": "component/memory_service",
        "name": "MemoryService",
        "entity_type": "component",
        "description": "Core persistence service",
        "observations": [
            {
                "id": 123,
                "content": "Uses SQLite storage"
            },
            {
                "id": 124,
                "content": "Implements async operations"
            }
        ],
        "relations": [
            {
                "id": 45,
                "from_id": "test/memory_test",
                "to_id": "component/memory_service",
                "relation_type": "validates",
                "context": "Main test suite"
            }
        ]
    }
    """

    id: str
    name: str
    entity_type: str
    description: Optional[str] = None
    observations: List[ObservationResponse] = []
    relations: List[RelationResponse] = []


class CreateEntityResponse(SQLAlchemyModel):
    """Response for create_entities operation.

    Returns complete information about all created entities,
    including their generated IDs, initial observations,
    and any established relations.

    Example Response:
    {
        "entities": [
            {
                "id": "component/search_service",
                "name": "SearchService",
                "entity_type": "component",
                "description": "Knowledge graph search",
                "observations": [
                    {
                        "id": 125,
                        "content": "Implements full-text search"
                    }
                ],
                "relations": []
            },
            {
                "id": "document/api_docs",
                "name": "API_Documentation",
                "entity_type": "document",
                "description": "API Reference",
                "observations": [
                    {
                        "id": 126,
                        "content": "Documents REST endpoints"
                    }
                ],
                "relations": []
            }
        ]
    }
    """

    entities: List[EntityResponse]


class SearchNodesResponse(SQLAlchemyModel):
    """Response for search operation.

    Returns matching entities with their complete information,
    plus the original query for reference.

    Example Response:
    {
        "matches": [
            {
                "id": "component/memory_service",
                "name": "MemoryService",
                "entity_type": "component",
                "description": "Core service",
                "observations": [...],
                "relations": [...]
            }
        ],
        "query": "memory"
    }

    Note: Each entity in matches includes full details
    just like EntityResponse.
    """

    matches: List[EntityResponse]
    query: str


class OpenNodesResponse(SQLAlchemyModel):
    """Response for retrieving specific entities.

    Returns complete Entity objects for all found entities.
    Entities that don't exist are silently skipped.

    Example Response:
    {
        "entities": [
            {
                "id": "component/memory_service",
                "name": "MemoryService",
                "entity_type": "component",
                "description": "Core service",
                "observations": [...],
                "relations": [...]
            }
        ]
    }
    """

    entities: List[EntityResponse]


class AddObservationsResponse(SQLAlchemyModel):
    """Response for adding observations.

    Returns the entity ID and details about all newly
    added observations.

    Example Response:
    {
        "entity_id": "component/memory_service",
        "observations": [
            {
                "id": 127,
                "content": "Added new feature"
            },
            {
                "id": 128,
                "content": "Fixed bug"
            }
        ]
    }
    """

    entity_id: EntityId
    observations: List[ObservationResponse]


class CreateRelationsResponse(SQLAlchemyModel):
    """Response for creating new relations.

    Returns complete information about all created relations,
    including their generated IDs.

    Example Response:
    {
        "relations": [
            {
                "id": 46,
                "from_id": "component/memory_service",
                "to_id": "component/database",
                "relation_type": "depends_on",
                "context": "Storage dependency"
            }
        ]
    }
    """

    relations: List[Relation]


class DeleteEntityResponse(SQLAlchemyModel):
    """Response indicating successful entity deletion.

    A simple boolean response confirming the delete operation
    completed successfully.

    Example Response:
    {
        "deleted": true
    }
    """

    deleted: bool


class DeleteRelationsResponse(SQLAlchemyModel):
    """Response indicating successful relation deletion.

    A simple boolean response confirming the delete operation
    completed successfully.

    Example Response:
    {
        "deleted": true
    }
    """

    deleted: bool


class DeleteObservationsResponse(SQLAlchemyModel):
    """Response indicating successful observation deletion.

    A simple boolean response confirming the delete operation
    completed successfully.

    Example Response:
    {
        "deleted": true
    }
    """

    deleted: bool
