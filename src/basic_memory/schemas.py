"""
Core pydantic models for basic-memory entities, observations, and relations.
These models define the schema for our core data types while remaining 
independent from storage/persistence concerns.
"""

from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, model_validator


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

    @model_validator(mode='before')
    @classmethod
    def generate_id(cls, data: dict) -> dict:
        """Generate an ID if one wasn't provided during instantiation"""
        if not data.get('id') and data.get('name'):
            timestamp = datetime.now(UTC).strftime("%Y%m%d")
            normalized_name = data['name'].lower().replace(" ", "-")
            data['id'] = f"{timestamp}-{normalized_name}-{uuid4().hex[:8]}"
        return data

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize entity, handling relations to prevent circular references"""
        # Get basic data without relations
        exclude = kwargs.pop('exclude', set())
        exclude.add('relations')
        basic_data = super().model_dump(exclude=exclude, **kwargs)

        # Add serialized relations if we have any
        if 'relations' not in exclude and self.relations:
            basic_data['relations'] = [
                relation.model_dump(**kwargs)
                for relation in self.relations
            ]

        return basic_data

    def file_name(self) -> str:
        """Get the markdown file name for this entity."""
        return f"{self.id}.md"