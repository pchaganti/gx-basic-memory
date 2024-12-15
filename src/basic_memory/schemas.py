"""Core pydantic models for basic-memory entities, observations, and relations."""
from typing import List, Optional, Annotated, TypeAlias
from annotated_types import Len
from pydantic import BaseModel, ConfigDict

# Base Models
Observation: TypeAlias = str

class Relation(BaseModel):
    """
    Represents a directed edge between entities in the knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    from_id: str
    to_id: str
    relation_type: str
    context: Optional[str] = None

class Entity(BaseModel):
    """
    Represents a node in our knowledge graph - could be a person, project,
    concept, etc. Each entity has a unique name, a type, and a list of
    associated observations.
    """
    id: Optional[str] = None
    name: str
    entity_type: str
    description: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []

    @property
    def file_path(self) -> str:
        """The relative file path for this entity."""
        return f"{id}.md"

# request input models

class AddObservationsRequest(BaseModel):
    """Schema for adding observations to an entity."""
    entity_id: str
    context: Optional[str] = None
    observations: List[Observation]

class CreateEntityRequest(BaseModel):
    """Request schema for create_entities tool."""
    entities: Annotated[List[Entity], Len(min_length=1)]

class SearchNodesRequest(BaseModel):
    """Request schema for search_nodes tool."""
    query: str

class OpenNodesRequest(BaseModel):
    """Request schema for open_nodes tool."""
    names: Annotated[List[str], Len(min_length=1)]

class CreateRelationsRequest(BaseModel):
    """Request schema for create_relations tool."""
    relations: List[Relation]

class DeleteEntityRequest(BaseModel):
    """Request schema for delete_entities tool."""
    names: List[str]

class DeleteObservationsRequest(BaseModel):
    """Request schema for delete_observations tool."""
    entity_id: str
    deletions: List[str]  # TODO: Make this more specific

# response output models

# Base output model for SQLAlchemy attribute conversion
class SQLAlchemyModel(BaseModel):
    """Base class for models that read from SQLAlchemy attributes."""
    model_config = ConfigDict(from_attributes=True)

class ObservationResponse(SQLAlchemyModel):
    """Schema for observation data returned from the service."""
    id: int
    content: Observation

class ObservationsResponse(SQLAlchemyModel):
    """Schema for bulk observation operation results."""
    entity_id: str
    observations: List[ObservationResponse]

class RelationResponse(Relation,SQLAlchemyModel):
    id: int

class EntityResponse(SQLAlchemyModel):
    """Schema for entity data returned from the service."""
    id: str 
    name: str
    entity_type: str
    description: Optional[str] = None
    observations: List[ObservationResponse] = []
    relations: List[RelationResponse] = []

class CreateEntityResponse(SQLAlchemyModel):
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
    relations: List[Relation]

class DeleteEntityResponse(SQLAlchemyModel):
    """Response for delete_entities tool."""
    deleted: List[str]

class DeleteObservationsResponse(SQLAlchemyModel):
    """Response for delete_observations tool."""
    entity_id: str
    deleted: List[Observation]