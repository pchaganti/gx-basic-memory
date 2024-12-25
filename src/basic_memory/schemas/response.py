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

import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field, AliasPath, AliasChoices

from basic_memory.schemas.base import Observation, Relation, PathId


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

    content: Observation


class RelationResponse(Relation, SQLAlchemyModel):
    """Response schema for relation operations.

    Extends the base Relation model with a unique ID that can be
    used for later modification or deletion.

    Example Response:
    {
        "from_id": "test/memory_test",
        "to_id": "component/memory_service",
        "relation_type": "validates",
        "context": "Comprehensive test suite"
    }
    """
    from_id: PathId = Field(
        # use the path_id from the associated Entity
        # or the from_id value
        validation_alias=AliasChoices(
            AliasPath('from_entity', 'path_id'),  
            'from_id',  
        )
    )
    to_id: PathId = Field(
        # use the path_id from the associated Entity
        # or the to_id value
        validation_alias=AliasChoices(
            AliasPath('to_entity', 'path_id'),  
            'to_id',  
        )
    )


class EntityResponse(SQLAlchemyModel):
    """Complete entity data returned from the service.

    This is the most comprehensive entity view, including:
    1. Basic entity details (id, name, type)
    2. All observations with their IDs
    3. All relations with their IDs
    4. Optional description

    Example Response:
    {
        "path_id": "component/memory_service",
        "name": "MemoryService",
        "entity_type": "component",
        "description": "Core persistence service",
        "observations": [
            {
                "content": "Uses SQLite storage"
            },
            {
                "content": "Implements async operations"
            }
        ],
        "relations": [
            {
                "from_id": "test/memory_test",
                "to_id": "component/memory_service",
                "relation_type": "validates",
                "context": "Main test suite"
            }
        ]
    }
    """

    path_id: PathId
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
                "path_id": "component/search_service",
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
                "path_id": "document/api_docs",
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
                "path_id": "component/memory_service",
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
                "path_id": "component/memory_service",
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


class DeleteEntitiesResponse(SQLAlchemyModel):
    """Response indicating successful entity deletion.

    A simple boolean response confirming the delete operation
    completed successfully.

    Example Response:
    {
        "deleted": true
    }
    """

    deleted: bool


class DocumentCreateResponse(SQLAlchemyModel):
    path: str
    checksum: str
    doc_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DocumentResponse(DocumentCreateResponse):
    content: str
