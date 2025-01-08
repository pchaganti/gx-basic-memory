"""Writer for knowledge entity markdown files."""

from basic_memory.models import Entity as EntityModel


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
            "id": entity.path_id,
            "type": entity.entity_type,
            "created": entity.created_at.isoformat(),
            "modified": entity.updated_at.isoformat(),
        }
        if entity.entity_metadata:
            frontmatter.update(entity.entity_metadata)
        return frontmatter

    async def format_content(self, entity: EntityModel, content: str = None) -> str:
        """Format entity content as markdown.
        
        Args:
            entity: Entity to format
            content: Optional raw content to use instead of generating structured content
            
        Returns:
            Formatted markdown content
        """
        # If raw content provided, use it directly
        if content is not None:
            return content

        # Otherwise, build structured content from entity data
        sections = []
        
        # Only add entity name as title if we don't have structured content
        # This prevents duplicate titles when raw content already has a title
        if not (entity.observations or entity.outgoing_relations):
            sections.extend([
                f"# {entity.name}",
                "",  # Empty line after title
            ])
            
            if entity.summary:
                sections.extend([entity.summary, ""])

        # Add observations if present
        if entity.observations:
            sections.extend([
                "## Observations",
                "<!-- Format: - [category] Content text #tag1 #tag2 (optional context) -->",
                "",  # Empty line after format comment
            ])
            
            for obs in entity.observations:
                line = f"- [{obs.category}] {obs.content}"
                if obs.context:
                    line += f" ({obs.context})"
                sections.append(line)
            sections.append("")  # Empty line after observations

        # Add relations if present
        if entity.outgoing_relations:
            sections.extend([
                "## Relations",
                "<!-- Format: - relation_type [[Entity]] (context) -->",
                "",  # Empty line after format comment
            ])
            
            for rel in entity.outgoing_relations:
                line = f"- {rel.relation_type} [[{rel.to_entity.name}]]"
                if rel.context:
                    line += f" ({rel.context})"
                sections.append(line)
            sections.append("")  # Empty line after relations

        # Return joined sections, ensure content isn't empty
        content = "\n".join(sections).strip()
        return content if content else f"# {entity.name}"
