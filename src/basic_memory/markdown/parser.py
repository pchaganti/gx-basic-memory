"""Parser for Basic Memory entity markdown files."""

from pathlib import Path
from typing import Dict, Any, Optional

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
    
    Parses files in the Knowledge Format, which includes:
    - YAML frontmatter
    - Markdown content with observations
    - Optional metadata section
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

    async def parse_content(self, content: str) -> EntityContent:
        """
        Parse entity content section.
        
        Args:
            content: Content section text
            
        Returns:
            Parsed EntityContent
            
        Raises:
            ParseError: If content doesn't match schema
        """
        try:
            return EntityContent.from_markdown(content)
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

    async def create_document(
        self, 
        frontmatter: EntityFrontmatter, 
        content: EntityContent, 
        metadata: EntityMetadata
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
        return Entity(
            frontmatter=frontmatter,
            content=content,
            metadata=metadata
        )