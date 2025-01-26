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
    
    def __str__(self) -> str:
        obs_string = f"[{self.category}] {self.content}"
        if self.tags:
            obs_string += " " + " ".join(f"#{tag}" for tag in sorted(self.tags))
        if self.context:
            obs_string += f" ({self.context})"
        return obs_string


class Relation(BaseModel):
    """A relation between entities."""

    type: str
    target: str
    context: Optional[str] = None
    
    def __str__(self) -> str:
        rel_string = f"{self.type} [[{self.target}]]"
        if self.context:
            rel_string += f" ({self.context})"
        return rel_string


class EntityFrontmatter(BaseModel):
    """Required frontmatter fields for an entity."""

    metadata: Optional[dict] = None

    @property
    def tags(self) -> List[str]:
        return self.metadata.get("tags") if self.metadata else []

    @property
    def title(self) -> str:
        return self.metadata.get("title") if self.metadata else None

    @property
    def type(self) -> str:
        return self.metadata.get("type", "note") if self.metadata else "note"

    @property
    def permalink(self) -> str:
        return self.metadata.get("permalink") if self.metadata else None

    @property
    def created(self) -> datetime:
        return self.metadata.get("created") if self.metadata else None

    @property
    def modified(self) -> datetime:
        return self.metadata.get("modified") if self.metadata else None


class EntityMarkdown(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""

    frontmatter: EntityFrontmatter
    content: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []
