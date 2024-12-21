"""Models for the markdown parser."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Observation(BaseModel):
    """An observation about an entity."""

    category: str
    content: str
    tags: List[str]
    context: Optional[str] = None


class Relation(BaseModel):
    """A relation between entities."""

    target: str  # The entity being linked to
    type: str  # The type of relation
    context: Optional[str] = None


class EntityFrontmatter(BaseModel):
    """Required frontmatter fields for an entity."""

    type: str
    id: str
    created: datetime
    modified: datetime
    tags: List[str]


class EntityMetadata(BaseModel):
    """Optional metadata fields for an entity (backmatter)."""

    metadata: Dict[str, Any] = {}


class EntityContent(BaseModel):
    """Content sections of an entity markdown file."""

    title: str
    description: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []
    context: Optional[str] = None


class Entity(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""

    frontmatter: EntityFrontmatter
    content: EntityContent 
    metadata: EntityMetadata = EntityMetadata()