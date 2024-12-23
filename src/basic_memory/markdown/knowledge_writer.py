"""Writer for knowledge entity markdown files."""

from datetime import datetime, UTC
from typing import Optional, Dict, Any

import yaml
from loguru import logger

from basic_memory.models import Entity as EntityModel


class KnowledgeWriter:
    """Formats entities into markdown files."""

    async def format_frontmatter(self, entity: EntityModel) -> dict:
        """Generate frontmatter metadata for entity."""
        now = datetime.now(UTC).isoformat()
        return {
            "type": entity.entity_type,
            "id": entity.id,
            "created": now,
            "modified": now
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

    async def format_content(self, entity: EntityModel, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Format entity content as markdown."""
        sections = [
            f"# {entity.name}\n"
        ]

        if entity.description:
            sections.extend([
                entity.description,
                ""
            ])
            
        if entity.observations:
            sections.extend([
                "## Observations",
                *[f"- {obs.content}" for obs in entity.observations],
                ""
            ])

        if entity.relations:
            sections.extend([
                "## Relations",
                *[f"- [[{rel.to_entity.name}]] {rel.relation_type}" for rel in entity.relations],
                ""
            ])

        if metadata:
            sections.append("\n")
            sections.append(await self.format_metadata(metadata))

        return "\n".join(sections)
