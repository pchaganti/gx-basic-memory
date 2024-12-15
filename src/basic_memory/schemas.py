"""Core pydantic models for basic-memory entities, observations, and relations."""
from typing import List, Optional, Annotated
from annotated_types import Len
from pydantic import BaseModel, ConfigDict

# Base output model for SQLAlchemy attribute conversion
class SQLAlchemyModel(BaseModel):
    """Base class for models that read from SQLAlchemy attributes."""
    model_config = ConfigDict(from_attributes=True)

# Base Models
class AddObservationsRequest(BaseModel):
    """Schema for adding observations to an entity."""
    entity_id: str
    context: Optional[str] = None
    observations: List[str]
    model_config = ConfigDict(populate_by_name=True)

class ObservationResponse(SQLAlchemyModel):
    """Schema for observation data returned from the service."""
    id: int
    content: str

class ObservationsResponse(SQLAlchemyModel):
    """Schema for bulk observation operation results."""
    entity_id: str
    observations: List[ObservationResponse]
    model_config = ConfigDict(populate_by_name=True)

class RelationRequest(BaseModel):
    """
    Represents a directed edge between entities in the knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    from_id: str
    to_id: str
    relation_type: str
    context: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class RelationResponse(SQLAlchemyModel):
    id: int
    from_id: str
    to_id: str
    relation_type: str
    context: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)

class EntityBase(BaseModel):
    id: Optional[str] = None
    name: str
    entity_type: str
    description: Optional[str] = None

    @property
    def file_path(self) -> str:
        """The relative file path for this entity."""
        return f"{id}.md"

    model_config = ConfigDict(from_attributes=True)

class EntityRequest(EntityBase):
    """
    Represents a node in our knowledge graph - could be a person, project,
    concept, etc. Each entity has a unique name, a type, and a list of
    associated observations.
    """
    observations: List[str] = []
    relations: List[RelationRequest] = []
    model_config = ConfigDict(populate_by_name=True)

class EntityResponse(EntityBase, SQLAlchemyModel):
    """Schema for entity data returned from the service."""
    observations: List[ObservationResponse] = []
    relations: List[RelationResponse] = []
    model_config = ConfigDict(populate_by_name=True)

# Tool Input Schemas
class CreateEntitiesRequest(BaseModel):
    """Input schema for create_entities tool."""
    entities: Annotated[List[EntityRequest], Len(min_length=1)]

class SearchNodesRequest(BaseModel):
    """Input schema for search_nodes tool."""
    query: str

class OpenNodesRequest(BaseModel):
    """Input schema for open_nodes tool."""
    names: Annotated[List[str], Len(min_length=1)]

class CreateRelationsRequest(BaseModel):
    """Input schema for create_relations tool."""
    relations: List[RelationRequest]

class DeleteEntitiesRequest(BaseModel):
    """Input schema for delete_entities tool."""
    names: List[str]

class DeleteObservationsRequest(BaseModel):
    """Input schema for delete_observations tool."""
    entity_id: str
    deletions: List[str]  # TODO: Make this more specific

class CreateEntitiesResponse(SQLAlchemyModel):
    """Response for create_entities tool."""
    entities: List[EntityResponse]

class SearchNodesResponse(SQLAlchemyModel):
    """Response for search_nodes tool."""
    matches: List[EntityResponse]
    query: str

class OpenNodesResponse(SQLAlchemyModel):
    """Response for open_nodes tool."""
    entities: List[EntityResponse]

class AddObservationsResponse(SQLAlchemyModel):
    """Response for add_observations tool."""
    entity_id: str
    observations: List[ObservationResponse]

class CreateRelationsResponse(SQLAlchemyModel):
    """Response for create_relations tool."""
    relations: List[RelationResponse]

class DeleteEntitiesResponse(SQLAlchemyModel):
    """Response for delete_entities tool."""
    deleted: List[str]

class DeleteObservationsResponse(SQLAlchemyModel):
    """Response for delete_observations tool."""
    entity_id: str
    deleted: List[str]