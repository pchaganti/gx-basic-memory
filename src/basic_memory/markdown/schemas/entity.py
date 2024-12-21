"""Models for the markdown parser."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from markdown_it import MarkdownIt
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

    @classmethod
    def from_text(cls, text: str) -> "EntityMetadata":
        """Parse metadata from text."""
        try:
            metadata = {}
            if text:  # Only parse if there's content
                for line in text.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()
            return cls(metadata=metadata)
        except Exception as e:
            raise ParseError(f"Failed to parse metadata: {e}") from e


class EntityContent(BaseModel):
    """Content sections of an entity markdown file."""

    title: str
    description: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []
    context: Optional[str] = None

    @classmethod
    def from_markdown(cls, text: str) -> "EntityContent":
        """Parse content from markdown text."""
        try:
            md = MarkdownIt()
            tokens = md.parse(text.strip())

            # State for parsing
            title = ""
            description = ""
            observations: List[Observation] = []
            relations: List[Relation] = []
            current_section = None

            # Track list items
            in_list_item = False
            list_item_tokens = []

            for token in tokens:
                if token.type == "heading_open":
                    if token.tag == "h1":
                        current_section = "title"
                    elif token.tag == "h2":
                        current_section = "section_name"

                elif token.type == "inline":
                    content = token.content.strip()

                    if current_section == "title":
                        title = content
                        current_section = "description"
                    elif current_section == "section_name":
                        current_section = content.lower()
                    elif current_section == "description":
                        if description:
                            description += " "
                        description += content
                    elif in_list_item:
                        list_item_tokens.append(token)

                elif token.type == "list_item_open":
                    in_list_item = True
                    list_item_tokens = []

                elif token.type == "list_item_close":
                    item_content = " ".join(t.content for t in list_item_tokens)
                    try:
                        if current_section == "observations":
                            if obs := Observation.from_line(item_content):
                                observations.append(obs)
                        elif current_section == "relations":
                            if rel := Relation.from_line(item_content):
                                relations.append(rel)
                    except ParseError:
                        # Skip malformed items
                        pass
                    in_list_item = False

            return cls(
                title=title,
                description=description,
                observations=observations,
                relations=relations,
            )

        except Exception as e:
            raise ParseError(f"Failed to parse markdown content: {e}") from e


class Entity(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""

    frontmatter: EntityFrontmatter
    content: EntityContent 
    metadata: EntityMetadata = EntityMetadata()