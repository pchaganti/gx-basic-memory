"""Parser for markdown files into Entity objects.

Uses markdown-it with plugins to parse structured data from markdown content.
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from dateparser import parse

from markdown_it import MarkdownIt
import frontmatter

from basic_memory.markdown.plugins import observation_plugin, relation_plugin
from basic_memory.markdown.schemas import (
    EntityMarkdown,
    EntityFrontmatter,
    EntityContent,
    Observation,
    Relation,
)


class EntityParser:
    """Parser for markdown files into Entity objects."""

    def __init__(self, base_path: Path):
        """Initialize parser with base path for relative permalink generation."""
        self.base_path = base_path.resolve()
        self.md = MarkdownIt().use(observation_plugin).use(relation_plugin)

    def relative_path(self, file_path: Path) -> str:
        """Get file path relative to base_path.

        Example:
            base_path: /project/root
            file_path: /project/root/design/models/data.md
            returns: "design/models/data"
        """
        # Get relative path and remove .md extension
        rel_path = file_path.resolve().relative_to(self.base_path)
        if rel_path.suffix.lower() == ".md":
            return str(rel_path.with_suffix(""))
        return str(rel_path)

    def parse_date(self, value: Any) -> Optional[datetime]:
        """Parse date strings using dateparser for maximum flexibility.
        
        Supports human friendly formats like:
        - 2024-01-15
        - Jan 15, 2024
        - 2024-01-15 10:00 AM
        - yesterday
        - 2 days ago
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                parsed = parse(value)
                if parsed:
                    return parsed
            except Exception:
                pass
        return None

    async def parse_file(self, file_path: Path) -> EntityMarkdown:
        """Parse markdown file into EntityMarkdown."""
        # Parse frontmatter and content using python-frontmatter
        post = frontmatter.load(str(file_path))

        # Extract or generate required fields
        permalink = post.metadata.get("permalink")
        file_stats = file_path.stat()

        # Parse frontmatter
        entity_frontmatter = EntityFrontmatter(
            type=str(post.metadata.get("type", "note")),
            permalink=permalink,
            title=str(post.metadata.get("title", file_path.name)),
            created=self.parse_date(post.metadata.get("created"))
            or datetime.fromtimestamp(file_stats.st_ctime),
            modified=self.parse_date(post.metadata.get("modified"))
            or datetime.fromtimestamp(file_stats.st_mtime),
            tags=self.parse_tags(post.metadata.get("tags", [])),
        )

        # Parse content for observations and relations using markdown-it
        observations = []
        relations = []

        for token in self.md.parse(post.content):
            # check for observations and relations
            if token.meta:
                if "observation" in token.meta:
                    obs = token.meta["observation"]
                    observation = Observation.model_validate(obs)
                    observations.append(observation)
                if "relations" in token.meta:
                    rels = token.meta["relations"]
                    relations.extend([Relation.model_validate(r) for r in rels])

        # Create EntityContent
        entity_content = EntityContent(
            content=post.content,
            observations=observations,
            relations=relations,
        )

        return EntityMarkdown(
            frontmatter=entity_frontmatter,
            content=entity_content,
        )

    def parse_tags(self, tags: Any) -> list[str]:
        """Parse tags into list of strings."""
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        if isinstance(tags, (list, tuple)):
            return [str(t).strip() for t in tags if str(t).strip()]
        return []
