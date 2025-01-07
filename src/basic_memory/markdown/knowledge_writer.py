"""Writer for knowledge entity markdown files."""

from basic_memory.models import Entity as EntityModel


class KnowledgeWriter:
    """Formats entities into markdown files."""

    async def format_frontmatter(self, entity: EntityModel) -> dict:
        """Generate frontmatter metadata for entity."""
        frontmatter = {
            "id": entity.path_id,
            "type": entity.entity_type,
            "created": entity.created_at.isoformat(),
            "modified": entity.updated_at.isoformat(),
        }
        if entity.entity_metadata:
            frontmatter.update(entity.entity_metadata)
        return frontmatter

    async def format_content(self, entity: EntityModel, content: str) -> str:
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

        # only outgoing relations are included in entity file
        if entity.outgoing_relations:
            sections.extend(
                [
                    "## Relations",
                    "<!-- Format: - relation_type [[Entity]] (context) -->"
                    "",  # Empty line after format comment
                ]
            )

            # Outgoing relations (entity is "from")
            for rel in entity.outgoing_relations:
                sections.append(f"- {rel.relation_type} [[{rel.to_entity.name}]] ")

        return "\n".join(sections)