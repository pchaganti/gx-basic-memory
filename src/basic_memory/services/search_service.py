"""Service for search operations."""

from typing import List, Optional, Set

from fastapi import BackgroundTasks
from loguru import logger

from basic_memory.models import Entity
from basic_memory.repository import EntityRepository
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.schemas.search import SearchQuery, SearchResult, SearchItemType


class SearchService:
    """Service for search operations."""

    def __init__(
        self,
        search_repository: SearchRepository,
        entity_repository: EntityRepository,
    ):
        self.repository = search_repository
        self.entity_repository = entity_repository

    async def init_search_index(self):
        """Create FTS5 virtual table if it doesn't exist."""
        await self.repository.init_search_index()

    async def reindex_all(self, background_tasks: Optional[BackgroundTasks] = None) -> None:
        """Reindex all content from database."""
        logger.info("Starting full reindex")

        # Clear and recreate search index
        await self.init_search_index()

        # Reindex all entities
        logger.debug("Indexing entities")
        entities = await self.entity_repository.find_all()
        for entity in entities:
            await self.index_entity(entity, background_tasks)

        logger.info("Reindex complete")

    async def search(
        self, query: SearchQuery, context: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search across all indexed content."""
        return await self.repository.search(query, context)

    def _generate_variants(self, text: str) -> Set[str]:
        """Generate text variants for better fuzzy matching.
        
        Creates variations of the text to improve match chances:
        - Original form
        - Lowercase form
        - Path segments (for permalinks)
        - Common word boundaries
        """
        variants = {text, text.lower()}
        
        # Add path segments
        if "/" in text:
            variants.update(p.strip() for p in text.split("/") if p.strip())
            
        # Add word boundaries
        variants.update(w.strip() for w in text.lower().split() if w.strip())
        
        # Add trigrams for fuzzy matching
        variants.update(text[i:i+3].lower() for i in range(len(text)-2))
        
        return variants

    async def index_entity(
        self, entity: Entity, background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Index an entity's content for search.
        
        Indexes:
        - Title and its variations for fuzzy matching
        - Path components for better findability
        - Content with context preservation
        """
        # Generate searchable content with variations
        content_parts = []
        
        # Add title variations
        title_variants = self._generate_variants(entity.title)
        content_parts.extend(title_variants)
        
        # Add summary if available
        if entity.summary:
            content_parts.append(entity.summary)
            
        # Add permalink variations
        permalink_variants = self._generate_variants(entity.permalink)
        content_parts.extend(permalink_variants)
        
        # Add file path components
        path_variants = self._generate_variants(entity.file_path)
        content_parts.extend(path_variants)

        # Join all parts and remove empty strings
        content = "\n".join(p for p in content_parts if p and p.strip())

        metadata = {
            "entity_type": entity.entity_type,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
        }

        # Queue indexing if background_tasks provided
        if background_tasks:
            background_tasks.add_task(
                self._do_index,
                title=entity.title,
                content=content,
                permalink=entity.permalink,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata=metadata,
            )
        else:
            await self._do_index(
                title=entity.title,
                content=content,
                permalink=entity.permalink,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata=metadata,
            )

    async def _do_index(
        self,
        title: str,
        content: str,
        permalink: str,
        file_path: str,
        type: SearchItemType,
        metadata: dict,
    ) -> None:
        """Actually perform the indexing."""
        await self.repository.index_item(
            title=title,
            content=content,
            permalink=permalink,
            file_path=file_path,
            type=type,
            metadata=metadata,
        )