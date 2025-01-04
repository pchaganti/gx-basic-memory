"""Writer for knowledge entity markdown files."""

from typing import Optional, Dict, Any

import yaml
from loguru import logger

from basic_memory.models import Entity as EntityModel


class KnowledgeWriter:
    """Formats entities into markdown files."""

    async def format_frontmatter(self, entity: EntityModel) -> dict:
        """Generate frontmatter metadata for entity."""
        return {
            "type": entity.entity_type,
            "id": entity.path_id,
            "created": entity.created_at.isoformat(),
            "modified": entity.updated_at.isoformat(),
        }

    async def format_metadata(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Format metadata section as YAML block."""
        if not metadata:
            return ""

        try:
            yaml_block = yaml.dump(metadata, sort_keys=False)
            return (
                "# Metadata\n"
                "<!-- anything below this line is for AI -->\n\n"
                "```yml\n"
                f"{yaml_block}"
                "```\n"
            )
        except Exception as e:
            logger.warning(f"Failed to format metadata YAML: {e}")
            return ""  # Skip metadata on error

    async def format_content(
        self, entity: EntityModel, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format entity content as markdown."""
        sections = [
            f"# {entity.name}\n",
            "",  # Empty line after name
        ]

        if entity.description:
            sections.extend([entity.description, ""])

        if entity.observations:
            sections.extend(
                [
                    "## Observations",
                    "<!-- Format: - [category] Content text #tag1 #tag2 (optional context) -->",
                    "",  # Empty line after format comment
                    *[
                        f"- [{obs.category}] {obs.content}"
                        + (f" ({obs.context})" if obs.context else "")
                        for obs in entity.observations
                    ],
                    "",
                ]
            )

        # Format outgoing and incoming relations separately
        if entity.to_relations or entity.from_relations:
            sections.extend(
                [
                    "## Relations",
                    "",  # Empty line after format comment
                ]
            )

            # Outgoing relations
            for rel in entity.to_relations:
                sections.append(f"- {rel.relation_type} [[{rel.from_entity.name}]] ")
            sections.append("")

        if metadata:
            sections.append("\n")
            sections.append(await self.format_metadata(metadata))

        return "\n".join(sections)
