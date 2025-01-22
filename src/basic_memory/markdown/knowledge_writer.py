"""Writer for knowledge entity markdown files."""

from typing import Optional

from loguru import logger

from basic_memory.markdown import EntityFrontmatter
from basic_memory.models import Entity as EntityModel, Observation


class KnowledgeWriter:
    """Formats entities into markdown files.

    Content handling:
    1. If raw content is provided, use it directly
    2. If structured data exists (observations/relations), generate structured content
    3. If neither, create basic content from name/summary
    """

    async def format_frontmatter(self, entity: EntityModel) -> dict:
        """Generate frontmatter metadata for entity."""
        frontmatter = {
            "permalink": entity.permalink,
            "type": entity.entity_type,
            "created": entity.created_at.isoformat(),
            "modified": entity.updated_at.isoformat(),
        }
        if entity.entity_metadata:
            frontmatter.update(entity.entity_metadata)
        return frontmatter

    async def format_observation(self, obs: Observation) -> str:
        """Format a single observation with category, content, tags and context."""
        line = f"- [{obs.category}] {obs.content}"

        # Add tags if present
        if obs.tags:
            line += " " + " ".join(f"#{tag}" for tag in sorted(obs.tags))

        # Add context if present
        if obs.context:
            line += f" ({obs.context})"

        return line

    async def format_content(self, entity: EntityModel, content: Optional[str] = None) -> str:
        """Format entity content as markdown.

        Args:
            entity: Entity to format
            content: Optional raw content to use instead of generating structured content

        Returns:
            Formatted markdown content
        """
        # If raw content provided, use it directly
        if content is not None:
            logger.debug("Content supplied to entity writer, using it directly")
            return content

        # Otherwise, build structured content from entity data
        sections = []

        # Only add entity title if we don't have structured content
        # This prevents duplicate titles when raw content already has a title
        if not (entity.observations or entity.outgoing_relations):
            sections.extend(
                [
                    f"# {entity.title}",
                    "",  # Empty line after title
                ]
            )

            if entity.summary:
                sections.extend([entity.summary, ""])

        # Add observations if present
        if entity.observations:
            sections.extend(
                [
                    "## Observations",
                    "<!-- Format: - [category] Content text #tag1 #tag2 (optional context) -->",
                    "",
                ]
            )

            for obs in entity.observations:
                sections.append(await self.format_observation(obs))
            sections.append("")

        # Add relations if present
        if entity.outgoing_relations:
            sections.extend(
                [
                    "## Relations",
                    "<!-- Format: - relation_type [[Entity]] (context) -->",
                    "",  # Empty line after format comment
                ]
            )

            for rel in entity.outgoing_relations:
                line = f"- {rel.relation_type} [[{rel.to_entity.title}]]"
                if rel.context:
                    line += f" ({rel.context})"
                sections.append(line)
            sections.append("")  # Empty line after relations

        # Return joined sections, ensure content isn't empty
        content = "\n".join(sections).strip()
        return content if content else f"# {entity.title}"
