"""Service for search operations."""

from typing import List, Optional

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

    async def index_entity(
        self, entity: Entity, background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Index an entity and its components.
        
        Creates multiple variations of content to improve matching:
        - Core identity (title, permalink)
        - Path components
        - Title variations
        - Observation content
        - Relation data
        """
        content_parts = []
        
        # Core identity - high weight terms
        weight_prefix = "title:"  # FTS5 will consider this a separate term
        content_parts.extend([
            entity.title.lower(),  # Original title
            f"{weight_prefix}{entity.title.lower()}",  # Weighted title
            entity.permalink.lower(),  # Full permalink
            *entity.permalink.split("/"),  # Path components
            entity.permalink.replace("/", " ").lower(),  # Path as search terms
        ])
        
        # Title variations for fuzzy matching
        words = entity.title.lower().split()
        content_parts.extend(words)  # Individual words
        if len(words) > 1:
            # Forward word combinations ("auth service" -> "auth", "auth service")
            content_parts.extend([" ".join(words[:i+1]) for i in range(len(words))])
            # Backward combinations ("auth service" -> "service", "auth service") 
            content_parts.extend([" ".join(words[i:]) for i in range(len(words))])
            
        # Summary if available
        if entity.summary:
            content_parts.extend([
                entity.summary,
                entity.summary.lower(),
            ])
                
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
                content=content,
                permalink=entity.permalink,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata=metadata,
            )
        else:
            await self._do_index(
                content=content,
                permalink=entity.permalink,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata=metadata,
            )

    async def _do_index(
        self, content: str, permalink: str, file_path: str, type: SearchItemType, metadata: dict
    ) -> None:
        """Actually perform the indexing."""
        await self.repository.index_item(
            content=content,
            permalink=permalink,
            file_path=file_path,
            type=type,
            metadata=metadata,
        )

    async def delete_by_permalink(self, permalink: str):
        """Delete an item from the search index."""
        await self.repository.delete_by_permalink(permalink)