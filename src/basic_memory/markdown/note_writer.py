"""Writer for note entity markdown files."""

from typing import Optional
from basic_memory.models import Entity as EntityModel


class NoteWriter:
    """Formats notes into markdown files with frontmatter."""

    async def format_frontmatter(self, entity: EntityModel) -> dict:
        """Generate frontmatter for note.
        
        Args:
            entity: The note entity to format frontmatter for

        Returns:
            Dictionary of frontmatter fields
        """
        frontmatter = {
            "id": entity.path_id,
            "type": entity.entity_type,
            "created": entity.created_at.isoformat(),
            "modified": entity.updated_at.isoformat()
        }
        # Add any entity_metadata that isn't None
        if entity.entity_metadata:
            frontmatter.update(entity.entity_metadata)
        return frontmatter

    async def format_content(
        self, 
        entity: EntityModel, 
        content: str,
    ) -> str:
        """Format note content as markdown.
        
        Args:
            entity: The note entity
            content: Raw content to format

        Returns:
            Formatted markdown content
        """
        return content.strip() # Just return the trimmed content