"""
Core pydantic models for basic-memory entities, observations, and relations.
These models define the schema for our core data types while remaining 
independent from storage/persistence concerns.
"""

from datetime import datetime, UTC
from typing import List, Optional
from pydantic import BaseModel


class Observation(BaseModel):
    """An atomic piece of information about an entity."""
    id: Optional[int] = None  # Let the database handle ID generation
    content: str
    context: Optional[str] = None


class ObservationCreate(BaseModel):
    """Schema for creating a new observation."""
    content: str


class Relation(BaseModel):
    """
    Represents a directed edge between entities in the knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    id: Optional[int] = None  # Let the database handle ID generation
    from_id: str             # Reference to Entity text ID
    to_id: str              # Reference to Entity text ID
    relation_type: str
    context: Optional[str] = None


class Entity(BaseModel):
    """
    Represents a node in our knowledge graph - could be a person, project,
    concept, etc. Each entity has a unique name, a type, and a list of
    associated observations.
    """
    id: str                         # Text ID for filesystem references
    name: str
    entity_type: str
    description: str = ""           # Match DB default
    references: str = ""            # Match DB default
    observations: List[Observation] = []
    relations: List[Relation] = []

    def file_name(self) -> str:
        """Get the markdown file name for this entity."""
        return f"{self.id}.md"