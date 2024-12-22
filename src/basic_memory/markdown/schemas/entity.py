"""Models for the markdown parser."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from basic_memory.utils.file_utils import ParseError
from basic_memory.markdown.schemas.observation import Observation
from basic_memory.markdown.schemas.relation import Relation


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

    @classmethod
    def from_markdown(cls, text: str) -> "EntityContent":
        """
        Parse content sections from markdown.
        
        Required sections:
        - Title (# Title)
        - Observations (## Observations)
        """
        try:
            lines = text.strip().split("\n")
            if not lines:
                raise ParseError("Content is empty")

            # Parse title (must start with # )
            title = ""
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    title = line[2:].strip()
                    description_start = i + 1
                    break
            if not title:
                raise ParseError("Missing title section (must start with '# ')")

            # Find section boundaries
            desc_lines = []
            obs_lines = []
            rel_lines = []
            
            current_section = "description"
            
            for line in lines[description_start:]:
                if line.startswith("## Observations"):
                    current_section = "observations"
                    continue
                elif line.startswith("## Relations"):
                    current_section = "relations"
                    continue
                
                if line.strip():  # Skip empty lines
                    if current_section == "description":
                        desc_lines.append(line)
                    elif current_section == "observations":
                        obs_lines.append(line)
                    elif current_section == "relations":
                        rel_lines.append(line)

            # Parse observations
            observations = []
            for line in obs_lines:
                if obs := Observation.from_line(line):
                    observations.append(obs)

            # Parse relations
            relations = []
            for line in rel_lines:
                if rel := Relation.from_line(line):
                    relations.append(rel)

            # Must have at least an observations section
            if not obs_lines:
                raise ParseError("Missing observations section")

            return cls(
                title=title,
                description="\n".join(desc_lines).strip() if desc_lines else None,
                observations=observations,
                relations=relations,
            )

        except Exception as e:
            if not isinstance(e, ParseError):
                raise ParseError(f"Failed to parse content: {str(e)}") from e
            raise


class EntityMetadata(BaseModel):
    """Optional metadata fields for an entity (backmatter)."""
    metadata: dict = {}


class Entity(BaseModel):
    """Complete entity combining frontmatter, content, and metadata."""
    frontmatter: EntityFrontmatter
    content: EntityContent
    metadata: EntityMetadata = EntityMetadata()