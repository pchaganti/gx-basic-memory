"""Service for resolving markdown links to permalinks."""

from typing import Optional, List

from loguru import logger

from basic_memory.services.service import BaseService
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.models import Entity
from basic_memory.services.exceptions import EntityNotFoundError


class LinkResolver(BaseService[Entity]):
    """Service for resolving markdown links to permalinks.
    
    Handles both exact and fuzzy link resolution using a combination of
    direct permalink lookup and search-based matching.
    """

    def __init__(self, entity_repository: EntityRepository):
        """Initialize with repositories."""
        super().__init__(entity_repository)
        
    async def resolve_link(
        self,
        link_text: str,
        source_permalink: Optional[str] = None
    ) -> str:
        """Resolve a markdown link to a permalink.
        
        Args:
            link_text: The text content of the link (without brackets)
            source_permalink: Optional permalink of the source document for context
            
        Returns:
            Resolved permalink, or original link text if no match found
        """
        logger.debug(f"Resolving link: {link_text} from source: {source_permalink}")
        
        # Clean link text
        clean_text = self._normalize_link_text(link_text)
        
        try:
            # Try exact permalink match first
            entity = await self.repository.get_by_permalink(clean_text)
            if entity:
                logger.debug(f"Found exact permalink match: {entity.permalink}")
                return entity.permalink
                
            # Fall back to title match if needed
            entity = await self.repository.get_by_title(clean_text)
            if entity:
                logger.debug(f"Found title match: {entity.permalink}")
                return entity.permalink
                
            # No match found - will be created
            logger.debug(f"No match found for link: {link_text}")
            return clean_text
            
        except Exception as e:
            logger.error(f"Error resolving link {link_text}: {e}")
            return clean_text

    def _normalize_link_text(self, link_text: str) -> str:
        """Normalize link text for matching.
        
        Args:
            link_text: Raw link text from markdown
            
        Returns:
            Normalized form for matching
        """
        # Strip whitespace
        text = link_text.strip()
        
        # Remove enclosing brackets if present
        if text.startswith('[[') and text.endswith(']]'):
            text = text[2:-2]
            
        # Handle Obsidian-style aliases
        if '|' in text:
            text = text.split('|')[0]
            
        return text