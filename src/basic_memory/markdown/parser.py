"""Parser for Basic Memory entity markdown files."""

from typing import Dict, Any, Optional, List

from loguru import logger

from basic_memory.markdown.base_parser import MarkdownParser, ParseError
from basic_memory.markdown.schemas import (
    Entity,
    EntityFrontmatter,
    EntityContent,
    EntityMetadata,
)


class EntityParser(MarkdownParser[Entity]):
    """
    Parser for entity markdown files.

    Entity files must have:
    - YAML frontmatter (type, id, created, modified, tags)
    - Title (# Title)
    - Optional description
    - Observations section (## Observations) with at least one observation
    - Relations section (## Relations)
    - Optional metadata section

    Observations format:
    - [category] Content text #tag1 #tag2 (optional context)

    Relations format:
    - relation_type [[Target Entity]] (optional context)
    """

    async def parse_frontmatter(self, frontmatter: Dict[str, Any]) -> EntityFrontmatter:
        """
        Parse entity frontmatter.

        Args:
            frontmatter: Parsed YAML frontmatter

        Returns:
            Parsed EntityFrontmatter

        Raises:
            ParseError: If frontmatter doesn't match schema
        """
        try:
            return EntityFrontmatter(**frontmatter)
        except Exception as e:
            logger.error(f"Invalid entity frontmatter: {e}")
            raise ParseError(f"Invalid entity frontmatter: {str(e)}") from e

    async def parse_content(self, title: str, sections: Dict[str, List[str]]) -> EntityContent:
        """
        Parse entity content section.

        Args:
            title: Document title
            sections: Section name -> list of lines mapping

        Returns:
            Parsed EntityContent

        Raises:
            ParseError: If content sections are invalid
        """
        try:
            # Get description (if any)
            description = None
            if "description" in sections:
                description = " ".join(sections["description"])

        # Parse observations (required)
        except Exception as e:
            logger.error(f"Invalid entity content: {e}")
            raise ParseError(f"Invalid entity content: {str(e)}") from e

    async def parse_metadata(self, metadata: Optional[Dict[str, Any]]) -> EntityMetadata:
        """
        Parse entity metadata section.

        Args:
            metadata: Optional metadata dictionary

        Returns:
            Parsed EntityMetadata

        Raises:
            ParseError: If metadata doesn't match schema
        """
        try:
            if not metadata:
                return EntityMetadata()
            return EntityMetadata(**metadata)
        except Exception as e:
            logger.error(f"Invalid entity metadata: {e}")
            raise ParseError(f"Invalid entity metadata: {str(e)}") from e

    async def create_document(  # pyright: ignore [reportIncompatibleMethodOverride]
        self, frontmatter: EntityFrontmatter, content: EntityContent, metadata: EntityMetadata
    ) -> Entity:
        """
        Create entity from parsed sections.

        Args:
            frontmatter: Parsed frontmatter
            content: Parsed content
            metadata: Parsed metadata

        Returns:
            Complete entity
        """
        return Entity(frontmatter=frontmatter, content=content, metadata=metadata)
