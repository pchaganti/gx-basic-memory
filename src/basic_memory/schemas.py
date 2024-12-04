"""
Core pydantic models for basic-memory entities, observations, and relations.
These models define the schema for our core data types while remaining 
independent from storage/persistence concerns.
"""

from datetime import datetime, UTC
from uuid import uuid4
from typing import List
from pydantic import BaseModel, model_validator


class Observation(BaseModel):
    """An atomic piece of information about an entity."""
    content: str


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

    @model_validator(mode='before')
    @classmethod 
    def generate_id_if_needed(cls, data: dict) -> dict:
        """Generate an ID if one wasn't provided during instantiation"""
        if not data.get('id') and data.get('name'):
            timestamp = datetime.now(UTC).strftime("%Y%m%d")
            normalized_name = data['name'].lower().replace(" ", "-")
            data['id'] = f"{timestamp}-{normalized_name}-{uuid4().hex[:8]}"
        return data


class Relation(BaseModel):
    """
    Represents a directed edge between two entities in our knowledge graph.
    Relations are always stored in active voice (e.g. "created", "teaches", etc.)
    """
    from_entity: str
    to_entity: str
    relation_type: str