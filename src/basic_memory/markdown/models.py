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
    """Frontmatter metadata for an entity."""

    type: str
    id: str
    created: datetime
    modified: datetime
    tags: List[str]
    status: Optional[str] = None
    version: Optional[int] = None
    priority: Optional[str] = None
    domain: Optional[str] = None
    maturity: Optional[str] = None
    owner: Optional[str] = None
    review_interval: Optional[str] = None
    last_reviewed: Optional[datetime] = None
    confidence: Optional[str] = None
    aliases: Optional[List[str]] = None


class EntityContent(BaseModel):
    """Content sections of an entity markdown file."""

    title: str
    description: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []
    context: Optional[str] = None
    metadata: Dict[str, Any] = {}


class Entity(BaseModel):
    """Complete entity combining frontmatter and content."""

    frontmatter: EntityFrontmatter
    content: EntityContent
