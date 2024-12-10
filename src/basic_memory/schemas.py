"""
Core pydantic models for basic-memory entities, observations, and relations.
These models define the schema for our core data types while remaining 
independent from storage/persistence concerns.
"""
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Annotated
from uuid import uuid4
from annotated_types import Gt, Len
from pydantic import BaseModel, Field, model_validator, ConfigDict

# Base Models
class ObservationIn(BaseModel):
    """Schema for creating a single observation."""
    content: str
    context: Optional[str] = None

class ObservationsIn(BaseModel):
    """Schema for adding observations to an entity."""
    entity_id: str = Field(alias="entityId")  # Maps to Entity.id
    observations: List[ObservationIn]
    model_config = ConfigDict(populate_by_name=True)

class ObservationOut(ObservationIn):
    """Schema for observation data returned from the service."""
    id: int
    model_config = ConfigDict(from_attributes=True)

class ObservationsOut(BaseModel):
    """Schema for bulk observation operation results."""
    entity_id: str = Field(alias="entityId")
    observations: List[ObservationOut]
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class RelationIn(BaseModel):
    """
    Represents a directed edge between entities in the knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    from_id: str = Field(alias="fromId")
    to_id: str = Field(alias="toId")              
    relation_type: str = Field(alias="relationType")
    context: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class RelationOut(BaseModel):
    id: int
    from_id: str = Field(alias="fromId")
    to_id: str = Field(alias="toId")
    relation_type: str = Field(alias="relationType")
    context: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class EntityBase(BaseModel):
    id: str = Field(default=None)  # Allow None during creation
    name: str
    entity_type: str = Field(alias="entityType")
    description: Optional[str] = None

    @model_validator(mode='after')
    def generate_id(self) -> 'EntityBase':
        """Generate an ID for this entity if not provided"""
        if not self.id:
            timestamp = datetime.now(UTC).strftime("%Y%m%d")
            normalized_name = self.name.lower().replace(" ", "-")
            self.id = f"{timestamp}-{normalized_name}"
        return self

    def file_name(self) -> str:
        """Get the markdown file name for this entity."""
        return f"{self.id}.md"

    model_config = ConfigDict(from_attributes=True)

class EntityIn(EntityBase):
    """
    Represents a node in our knowledge graph - could be a person, project,
    concept, etc. Each entity has a unique name, a type, and a list of
    associated observations.
    """
    observations: List[ObservationIn] = []
    relations: List[RelationIn] = []
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class EntityOut(EntityBase):
    """Schema for entity data returned from the service."""
    observations: List[ObservationOut] = []
    relations: List[RelationOut] = []
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

# Tool Input Schemas
class CreateEntitiesInput(BaseModel):
    """Input schema for create_entities tool."""
    entities: Annotated[List[EntityIn], Len(min_length=1)]

class SearchNodesInput(BaseModel):
    """Input schema for search_nodes tool."""
    query: str

class OpenNodesInput(BaseModel):
    """Input schema for open_nodes tool."""
    names: Annotated[List[str], Len(min_length=1)]

class AddObservationsInput(BaseModel):
    """Input schema for add_observations tool."""
    entity_id: str = Field(alias="entityId")
    observations: List[ObservationIn]
    model_config = ConfigDict(populate_by_name=True)

class CreateRelationsInput(BaseModel):
    """Input schema for create_relations tool."""
    relations: List[RelationIn]

class DeleteEntitiesInput(BaseModel):
    """Input schema for delete_entities tool."""
    names: List[str]

class DeleteObservationsInput(BaseModel):
    """Input schema for delete_observations tool."""
    deletions: List[Dict[str, Any]]  # TODO: Make this more specific

# Tool Response Schemas
class CreateEntitiesResponse(BaseModel):
    """Response for create_entities tool."""
    entities: List[EntityOut]
    model_config = ConfigDict(from_attributes=True)

class SearchNodesResponse(BaseModel):
    """Response for search_nodes tool."""
    matches: List[EntityOut]
    query: str
    model_config = ConfigDict(from_attributes=True)

class OpenNodesResponse(BaseModel):
    """Response for open_nodes tool."""
    entities: List[EntityOut]
    model_config = ConfigDict(from_attributes=True)

class AddObservationsResponse(BaseModel):
    """Response for add_observations tool."""
    entity_id: str
    added_observations: List[ObservationOut]
    model_config = ConfigDict(from_attributes=True)

class CreateRelationsResponse(BaseModel):
    """Response for create_relations tool."""
    relations: List[RelationOut]
    model_config = ConfigDict(from_attributes=True)

class DeleteEntitiesResponse(BaseModel):
    """Response for delete_entities tool."""
    deleted: List[str]
    model_config = ConfigDict(from_attributes=True)

class DeleteObservationsResponse(BaseModel):
    """Response for delete_observations tool."""
    entity_id: str
    deleted: List[str]
    model_config = ConfigDict(from_attributes=True)