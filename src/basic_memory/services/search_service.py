"""Service for search operations."""

from typing import List, Optional

from basic_memory.repository.search_repository import SearchRepository
from basic_memory.schemas.search import SearchQuery, SearchResult


class SearchService:
    """Service for search operations."""

    def __init__(self, search_repository: SearchRepository):
        self.repository = search_repository

    async def init_search_index(self):
        """Create FTS5 virtual table if it doesn't exist."""
        await self.repository.init_search_index()

    async def search(
        self, query: SearchQuery, context: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search across all indexed content."""
        return await self.repository.search(query, context)

    async def index_entity(self, entity, background_tasks=None):
        """Index an entity and its components."""
        # Build searchable content
        content = "\n".join(
            [
                entity.name,
                entity.description or "",
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
                type="entity",
                metadata=metadata,
            )
        else:
            await self._do_index(
                content=content,
                path_id=entity.path_id,
                file_path=entity.file_path,
                type="entity",
                metadata=metadata,
            )

    async def _do_index(self, **kwargs):
        """Actually perform the indexing."""
        await self.repository.index_item(**kwargs)
