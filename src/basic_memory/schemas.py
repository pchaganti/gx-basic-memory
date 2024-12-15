"""Core pydantic models for basic-memory entities, observations, and relations."""
from typing import List, Optional, Dict, Any, Annotated
from annotated_types import Len
from pydantic import BaseModel, ConfigDict

# Base output model for SQLAlchemy attribute conversion
class SQLAlchemyOut(BaseModel):
    """Base class for models that read from SQLAlchemy attributes."""
    model_config = ConfigDict(from_attributes=True)

# Base Models
class ObservationsIn(BaseModel):
    """Schema for adding observations to an entity."""
    entity_id: str
    context: Optional[str] = None
    observations: List[str]
    model_config = ConfigDict(populate_by_name=True)

class ObservationOut(SQLAlchemyOut):
    """Schema for observation data returned from the service."""
    id: int
    content: str

class ObservationsOut(SQLAlchemyOut):
    """Schema for bulk observation operation results."""
    entity_id: str
    observations: List[ObservationOut]
    model_config = ConfigDict(populate_by_name=True)

class RelationIn(BaseModel):
    """
    Represents a directed edge between entities in the knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    from_id: str
    to_id: str
    relation_type: str
    context: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class RelationOut(SQLAlchemyOut):
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

class EntityIn(EntityBase):
    """
    Represents a node in our knowledge graph - could be a person, project,
    concept, etc. Each entity has a unique name, a type, and a list of
    associated observations.
    """
    observations: List[str] = []
    relations: List[RelationIn] = []
    model_config = ConfigDict(populate_by_name=True)

class EntityOut(EntityBase, SQLAlchemyOut):
    """Schema for entity data returned from the service."""
    observations: List[ObservationOut] = []
    relations: List[RelationOut] = []
    model_config = ConfigDict(populate_by_name=True)

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

class AddObservationsInput(ObservationsIn):
    """Input schema for add_observations tool."""
    pass

class CreateRelationsInput(BaseModel):
    """Input schema for create_relations tool."""
    relations: List[RelationIn]

class DeleteEntitiesInput(BaseModel):
    """Input schema for delete_entities tool."""
    names: List[str]

class DeleteObservationsInput(BaseModel):
    """Input schema for delete_observations tool."""
    entity_id: str
    deletions: List[Dict[str, Any]]  # TODO: Make this more specific

# Tool Response Schemas
class CreateEntitiesResponse(SQLAlchemyOut):
    """Response for create_entities tool."""
    entities: List[EntityOut]

class SearchNodesResponse(SQLAlchemyOut):
    """Response for search_nodes tool."""
    matches: List[EntityOut]
    query: str

class OpenNodesResponse(SQLAlchemyOut):
    """Response for open_nodes tool."""
    entities: List[EntityOut]

class AddObservationsResponse(SQLAlchemyOut):
    """Response for add_observations tool."""
    entity_id: str
    added_observations: List[ObservationOut]

class CreateRelationsResponse(SQLAlchemyOut):
    """Response for create_relations tool."""
    relations: List[RelationOut]

class DeleteEntitiesResponse(SQLAlchemyOut):
    """Response for delete_entities tool."""
    deleted: List[str]

class DeleteObservationsResponse(SQLAlchemyOut):
    """Response for delete_observations tool."""
    entity_id: str
    deleted: List[str]