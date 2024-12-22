"""Schema models for entity markdown files."""
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel

from basic_memory.markdown.schemas.observation import Observation
from basic_memory.markdown.schemas.relation import Relation
from basic_memory.utils.file_utils import ParseError


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
    metadata: Dict[str, Any] = {}


class Entity(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""
    frontmatter: EntityFrontmatter
    content: EntityContent
    metadata: EntityMetadata = EntityMetadata()