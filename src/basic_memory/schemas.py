"""
Core pydantic models for basic-memory entities, observations, and relations.
These models define the schema for our core data types while remaining 
independent from storage/persistence concerns.
"""

from datetime import datetime, UTC
from uuid import uuid4
from typing import List, Optional, ForwardRef, Dict, Any
from pydantic import BaseModel, model_validator


class Observation(BaseModel):
    """An atomic piece of information about an entity."""
    content: str


class ObservationCreate(BaseModel):
    """Schema for creating a new observation."""
    content: str


class RelationCreate(BaseModel):
    """Schema for creating a new relation via the MCP tool interface."""
    from_: str = None  # Raw entity name from MCP tool
    to: str
    relationType: str

    # Handle the 'from' field which is a Python keyword
    @model_validator(mode='before')
    @classmethod
    def handle_from_field(cls, data: dict) -> dict:
        """Convert 'from' to 'from_' if present"""
        if 'from' in data:
            data['from_'] = data.pop('from')
        return data

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert back to format with 'from' field"""
        data = super().model_dump(**kwargs)
        if 'from_' in data:
            data['from'] = data.pop('from_')
        return data


class Relation(BaseModel):
    """
    Represents a directed edge between entities in the knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    id: str
    from_entity: 'Entity'
    to_entity: 'Entity'
    relation_type: str
    context: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def generate_id_if_needed(cls, data: dict) -> dict:
        """Generate an ID if one wasn't provided"""
        if not data.get('id'):
            data['id'] = f"rel-{uuid4().hex[:8]}"
        return data

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to storage format with entity IDs"""
        return {
            'id': self.id,
            'from_id': self.from_entity.id,
            'to_id': self.to_entity.id,
            'relation_type': self.relation_type,
            'context': self.context
        }


class Entity(BaseModel):
    """
    Represents a node in our knowledge graph - could be a person, project,
    concept, etc. Each entity has a unique name, a type, and a list of
    associated observations.
    """
    id: str
    name: str
    entity_type: str
    observations: List[Observation] = []
    relations: List[Relation] = []

    @model_validator(mode='before')
    @classmethod
    def generate_id_if_needed(cls, data: dict) -> dict:
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


# Update forward refs
Entity.model_rebuild()
Relation.model_rebuild()