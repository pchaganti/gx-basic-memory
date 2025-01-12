"""Core pydantic models for basic-memory entities, observations, and relations.

This module defines the foundational data structures for the knowledge graph system.
The graph consists of entities (nodes) connected by relations (edges), where each
entity can have multiple observations (facts) attached to it.

Key Concepts:
1. Entities are nodes storing factual observations
2. Relations are directed edges between entities using active voice verbs
3. Observations are atomic facts/notes about an entity
4. Everything is stored in both SQLite and markdown files
"""
import mimetypes
import re
from enum import Enum
from typing import List, Optional, Annotated, Dict

from annotated_types import MinLen, MaxLen
from pydantic import BaseModel, BeforeValidator, Field, model_validator, ValidationError


def to_snake_case(name: str) -> str:
    """Convert a string to snake_case.

    Examples:
        BasicMemory -> basic_memory
        Memory Service -> memory_service
        memory-service -> memory_service
        Memory_Service -> memory_service
    """
    name = name.strip()
    
    # Replace spaces and hyphens and . with underscores
    s1 = re.sub(r"[\s\-\\.]", "_", name)

    # Insert underscore between camelCase
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)

    # Convert to lowercase
    return s2.lower()


def validate_path_format(path: str) -> str:
    """Validate path has the correct format: not empty."""
    if not path or not isinstance(path, str):
        raise ValueError("Path must be a non-empty string")

    return path



class ObservationCategory(str, Enum):
    """Categories for structuring observations.

    Categories help organize knowledge and make it easier to find later:
    - tech: Implementation details and technical notes
    - design: Architecture decisions and patterns
    - feature: User-facing capabilities
    - note: General observations (default)
    - issue: Problems or concerns
    - todo: Future work items

    Categories are case-insensitive for easier use.
    """
    TECH = "tech"
    DESIGN = "design"
    FEATURE = "feature"
    NOTE = "note"
    ISSUE = "issue"
    TODO = "todo"

    @classmethod
    def _missing_(cls, value: str) -> "ObservationCategory":
        """Handle case-insensitive lookup."""
        try:
            return cls(value.lower())
        except ValueError:
            return None
        
        
PathId = Annotated[str, BeforeValidator(to_snake_case), BeforeValidator(validate_path_format)]
"""Unique identifier in format '{path}/{normalized_name}'."""

Observation = Annotated[
    str, 
    BeforeValidator(str.strip),  # Clean whitespace
    MinLen(1),  # Ensure non-empty after stripping
    MaxLen(1000)  # Keep reasonable length
]
"""A single piece of information about an entity. Must be non-empty and under 1000 characters.
"""

EntityType = Annotated[str, BeforeValidator(to_snake_case), MinLen(1), MaxLen(200)]
"""Classification of entity (e.g., 'person', 'project', 'concept'). """

ALLOWED_CONTENT_TYPES = {
    'text/markdown',
    'text/plain',
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/svg+xml',
}

ContentType = Annotated[
    str, 
    BeforeValidator(str.lower),
    Field(pattern=r'^[\w\-\+\.]+/[\w\-\+\.]+$'),
    Field(json_schema_extra={"examples": list(ALLOWED_CONTENT_TYPES)})
]



RelationType = Annotated[str, BeforeValidator(to_snake_case), MinLen(1), MaxLen(200)]
"""Type of relationship between entities. Always use active voice present tense."""


class Relation(BaseModel):
    """Represents a directed edge between entities in the knowledge graph.

    Relations are directed connections stored in active voice (e.g., "created", "depends_on").
    The from_path_id represents the source or actor entity, while to_path_id represents the target
    or recipient entity.
    """

    from_id: PathId
    to_id: PathId
    relation_type: RelationType
    context: Optional[str] = None


class Entity(BaseModel):
    """Represents a node in our knowledge graph - could be a person, project, concept, etc.

    Each entity has:
    - A title 
    - An entity type (for classification)
    - A list of observations (facts/notes about the entity)
    - Optional relations to other entities
    - Optional description for high-level overview
    """

    title: str
    entity_type: EntityType
    entity_metadata: Optional[Dict] = Field(default=None, description="Optional metadata")
    content: Optional[str] = None
    summary: Optional[str] = None
    content_type: ContentType = Field(
        description="MIME type of the content (e.g. text/markdown, image/jpeg)",
        examples=["text/markdown", "image/jpeg"]
    ) 
    observations: List[Observation] = []

    @property
    def path_id(self) -> PathId:
        """Get the path ID in format {snake_case_title}."""
        normalized_name = to_snake_case(self.title)
        return normalized_name

    @property
    def file_path(self):
        """Get the file path for this entity based on its path_id."""
        return f"{self.path_id}.md"

    @model_validator(mode='before')
    @classmethod
    def infer_content_type(cls, data: Dict) -> Dict:
        """Infer content_type from file_path if not provided."""
        if 'content_type' not in data:
            # Get path from either file_path or construct from path_id
            file_path = data.get('file_path') or f"{data.get('name')}.md"
            
            if not file_path:
                raise ValidationError("Either file_path or name must be provided")
            mime_type, _ = mimetypes.guess_type(file_path)
            data['content_type'] = mime_type or 'text/plain'

        return data