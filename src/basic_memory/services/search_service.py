"""Service for search operations."""

from typing import List, Optional, Any

from fastapi import BackgroundTasks
from loguru import logger

from basic_memory.models import Entity
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.services.entity_service import EntityService
from basic_memory.schemas.search import SearchQuery, SearchResult, SearchItemType


class SearchService:
    """Service for search operations."""

    def __init__(
        self,
        search_repository: SearchRepository,
        entity_service: EntityService,
    ):
        self.repository = search_repository
        self.entity_service = entity_service

    async def init_search_index(self):
        """Create FTS5 virtual table if it doesn't exist."""
        await self.repository.init_search_index()
        
    async def reindex_all(
        self,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Reindex all content from database."""
        logger.info("Starting full reindex")
        
        # Clear and recreate search index
        await self.init_search_index()
        
        # Reindex all entities
        logger.debug("Indexing entities")
        entities = await self.entity_service.get_all()
        for entity in entities:
            await self.index_entity(entity, background_tasks)
                        
        logger.info("Reindex complete")

    async def search(
        self,
        query: SearchQuery,
        context: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search across all indexed content."""
        return await self.repository.search(query, context)

    async def index_entity(
        self,
        entity: Entity,  
        background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Index an entity and its components."""
        # Build searchable content
        content = "\n".join(
            [
                entity.name,
                entity.summary or "",
                # Add observations
                *[f"{obs.category}: {obs.content}" for obs in entity.observations],
                # Add relations
                *[
                    f"{rel.relation_type} {rel.to_id}: {rel.context or ''}"
                    for rel in entity.relations
                ],
            ]
        )

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
                path_id=entity.path_id,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata=metadata,
            )
        else:
            await self._do_index(
                content=content,
                path_id=entity.path_id,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata=metadata,
            )

    async def _do_index(
        self,
        content: str,
        path_id: str,
        file_path: str,
        type: SearchItemType,
        metadata: dict
    ) -> None:
        """Actually perform the indexing."""
        await self.repository.index_item(
            content=content,
            path_id=path_id,
            file_path=file_path,
            type=type,
            metadata=metadata
        )
        
    async def delete_by_path_id(self, path_id: str):
        """Delete an item from the search index."""
        await self.repository.delete_by_path_id(path_id)