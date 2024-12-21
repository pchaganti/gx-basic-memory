"""Models for the markdown parser."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from basic_memory.markdown.exceptions import ParseError
from basic_memory.markdown.schemas.observation import Observation
from basic_memory.markdown.schemas.relation import Relation

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class EntityFrontmatter(BaseModel):
    """Required frontmatter fields for an entity."""

    type: str
    id: str
    created: datetime
    modified: datetime
    tags: List[str]

    @classmethod
    def from_text(cls, text: str) -> "EntityFrontmatter":
        """Parse frontmatter from YAML-style text."""
        try:
            frontmatter_data = {}
            for line in text.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter_data[key.strip()] = value.strip()

            # Handle tags specially
            if isinstance(frontmatter_data.get("tags"), str):
                frontmatter_data["tags"] = [t.strip() for t in frontmatter_data["tags"].split(",")]

            return cls(**frontmatter_data)
        except Exception as e:
            raise ParseError(f"Failed to parse frontmatter: {e}") from e


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