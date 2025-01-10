"""Parser for markdown files into Entity objects.

Uses markdown-it with plugins to parse structured data from markdown content.
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Optional

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
        """Initialize parser with base path for relative path_id generation."""
        self.base_path = base_path.resolve()
        self.md = (MarkdownIt()
                   .use(observation_plugin)
                   .use(relation_plugin))

    def get_path_id(self, file_path: Path) -> str:
        """Get path_id from file path relative to base_path.

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
        """Parse various date formats into datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return None

    async def parse_file(self, file_path: Path) -> EntityMarkdown:
        """Parse markdown file into EntityMarkdown."""
        # Parse frontmatter and content using python-frontmatter
        post = frontmatter.load(str(file_path))

        # Extract or generate required fields
        path_id = post.metadata.get("id") or self.get_path_id(file_path)
        stats = file_path.stat()

        # Parse frontmatter
        entity_frontmatter = EntityFrontmatter(
            type=str(post.metadata.get("type", "note")),
            id=path_id,
            title=str(post.metadata.get("title", file_path.name)),
            created=self.parse_date(post.metadata.get("created"))
            or datetime.fromtimestamp(stats.st_ctime),
            modified=self.parse_date(post.metadata.get("modified"))
            or datetime.fromtimestamp(stats.st_mtime),
            tags=self.parse_tags(post.metadata.get("tags", [])),
        )

        # Parse content for observations and relations using markdown-it
        observations, relations = await self.parse_observations_and_relations(post.content)

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

    async def parse_observations_and_relations(
        self, content: str
    ) -> tuple[list[Observation], list[Relation]]:
        tokens = self.md.parse(content)
        # Extract observations and relations from token meta
        observations = []
        relations = []
        for token in tokens:
            if token.meta:  # Token might not have meta
                if "observation" in token.meta:
                    obs = token.meta["observation"]
                    observation = Observation.model_validate(obs)
                    observations.append(observation)
                if "relations" in token.meta:
                    rels = token.meta["relations"]
                    relations.extend([Relation.model_validate(r) for r in rels])
        return observations, relations

    def parse_tags(self, tags: Any) -> list[str]:
        """Parse tags into list of strings."""
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        if isinstance(tags, (list, tuple)):
            return [str(t).strip() for t in tags if str(t).strip()]
        return []
