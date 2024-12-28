"""Schema models for entity markdown files."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class Observation(BaseModel):
    """An observation about an entity."""

    category: Optional[str] = None
    content: str
    tags: Optional[List[str]] = None
    context: Optional[str] = None


class Relation(BaseModel):
    """A relation between entities."""

    type: str
    target: str
    context: Optional[str] = None


class EntityFrontmatter(BaseModel):
    """Required frontmatter fields for an entity."""

    type: str
    id: str
    created: datetime
    modified: datetime
    tags: List[str]


class EntityContent(BaseModel):
    """Content sections of an entity markdown file."""

    title: str
    description: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []
    context: Optional[str] = None


class EntityMetadata(BaseModel):
    """Optional metadata for an entity."""

    # Changed from 'metadata' to 'data' to avoid pydantic special field name
    data: Dict[str, Any] = {}


class EntityMarkdown(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""

    frontmatter: EntityFrontmatter
    content: EntityContent
    entity_metadata: EntityMetadata = EntityMetadata()
