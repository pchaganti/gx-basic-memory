"""Request schemas for interacting with the knowledge graph."""

from typing import List, Optional, Annotated, Dict, Any
from annotated_types import MaxLen, MinLen

from pydantic import BaseModel, StringConstraints

from basic_memory.schemas.base import Observation, Entity, Relation, PathId, ObservationCategory, EntityType


class ObservationCreate(BaseModel):
    """A single observation with category, content, and optional context."""

    category: ObservationCategory = ObservationCategory.NOTE
    content: Observation 


class AddObservationsRequest(BaseModel):
    """Add new observations to an existing entity.

    Observations are atomic pieces of information about the entity.
    Each observation should be a single fact or note that adds value
    to our understanding of the entity.
    """

    path_id: PathId
    context: Optional[str] = None
    observations: List[ObservationCreate]


class CreateEntityRequest(BaseModel):
    """Create one or more new entities in the knowledge graph.

    Entities represent nodes in the knowledge graph. They can be created
    with initial observations and optional descriptions. Entity IDs are
    automatically generated from the type and name.
    
    Observations will be assigned the default category of 'note'.
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
    - If a category is specified, only entities with that category are returned

    Example Queries:
    - "memory" - Find entities related to memory systems
    - "SQLite" - Find database-related components
    - "test" - Find test-related entities
    - "implementation" - Find concrete implementations
    - "service" - Find service components

    Note: Currently uses SQL ILIKE for matching. Wildcard (*) searches
    and full-text search capabilities are planned for future versions.
    """

    query: Annotated[str, MinLen(1), MaxLen(200)]
    category: Optional[ObservationCategory] = None


class OpenNodesRequest(BaseModel):
    """Retrieve specific entities by their IDs.

    Used to load complete entity details including all observations
    and relations. Particularly useful for following relations
    discovered through search.
    """

    path_ids: Annotated[List[PathId], MinLen(1)]


class CreateRelationsRequest(BaseModel):

    relations: List[Relation]


## update

class UpdateEntityRequest(BaseModel):
    """Request to update an existing entity."""
    name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    description: Optional[str] = None
    content: Optional[str] = None
    entity_metadata: Optional[Dict[str, Any]] = None


DocumentPathId = Annotated[
    str, StringConstraints(pattern=r"^[a-zA-Z0-9_/.-]+\.md$"), MinLen(1), MaxLen(255)
]


class DocumentRequest(BaseModel):
    path_id: DocumentPathId
    content: str
    doc_metadata: Optional[Dict[str, Any]] = None
