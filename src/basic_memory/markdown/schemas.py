"""Schema models for entity markdown files."""

from datetime import datetime
from typing import List, Optional

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

    title: str
    type: str
    permalink: Optional[str] = None
    created: datetime
    modified: datetime
    tags: List[str]


class EntityContent(BaseModel):
    """Content sections of an entity markdown file."""

    content: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []


class EntityMarkdown(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""

    frontmatter: EntityFrontmatter
    content: EntityContent
