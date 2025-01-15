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
        return await self.repository.search(query)

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
        variants.update(text[i : i + 3].lower() for i in range(len(text) - 2))

        return variants

    async def index_entity(
        self, entity: Entity, background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Index an entity's content for search.

        Each type gets its own row in the search index with appropriate metadata
        and type-specific fields populated.
        - Content with context preservation
        """
        content_parts = []
        title_variants = self._generate_variants(entity.title)
        content_parts.extend(title_variants)

        if entity.summary:
            content_parts.append(entity.summary)

        content_parts.extend(self._generate_variants(entity.permalink))
        content_parts.extend(self._generate_variants(entity.file_path))
        
        entity_content = "\n".join(p for p in content_parts if p and p.strip())

        # Index entity
        if background_tasks:
            background_tasks.add_task(
                self._do_index,
                id=entity.id,
                title=entity.title,
                content=entity_content,
                permalink=entity.permalink,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata={
                    "entity_type": entity.entity_type,
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat(),
                }
            )
        else:
            await self._do_index(
                id=entity.id,
                title=entity.title,
                content=entity_content,
                permalink=entity.permalink,
                file_path=entity.file_path,
                type=SearchItemType.ENTITY,
                metadata={
                    "entity_type": entity.entity_type,
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat(),
                }
            )

        # Index each observation
        for obs in entity.observations:
            if background_tasks:
                background_tasks.add_task(
                    self._do_index,
                    id=obs.id,
                    title=f"{obs.category}: {obs.content[:50]}...",
                    content=obs.content,
                    permalink=f"{entity.permalink}/observations/{obs.id}",
                    file_path=entity.file_path,
                    type=SearchItemType.OBSERVATION,
                    metadata={
                        "entity_id": entity.id,
                        "category": obs.category,
                        "created_at": obs.created_at.isoformat(),
                        "updated_at": obs.updated_at.isoformat(),
                        "tags": obs.tags
                    }
                )
            else:
                await self._do_index(
                    id=obs.id,
                    title=f"{obs.category}: {obs.content[:50]}...",
                    content=obs.content,
                    permalink=f"{entity.permalink}/observations/{obs.id}",
                    file_path=entity.file_path,
                    type=SearchItemType.OBSERVATION,
                    metadata={
                        "entity_id": entity.id,
                        "category": obs.category,
                        "created_at": obs.created_at.isoformat(),
                        "updated_at": obs.updated_at.isoformat(),
                        "tags": obs.tags
                    }
                )

        # Index each relation
        for rel in entity.relations:
            if background_tasks:
                background_tasks.add_task(
                    self._do_index,
                    id=rel.id,
                    title=f"{rel.relation_type}",
                    content=rel.context or "",
                    permalink=f"{entity.permalink}/relations/{rel.id}",
                    file_path=entity.file_path,
                    type=SearchItemType.RELATION,
                    metadata={
                        "from_id": rel.from_id,
                        "to_id": rel.to_id,
                        "created_at": rel.created_at.isoformat(),
                        "updated_at": rel.updated_at.isoformat()
                    }
                )
            else:
                await self._do_index(
                    id=rel.id,
                    title=f"{rel.relation_type}",
                    content=rel.context or "",
                    permalink=f"{entity.permalink}/relations/{rel.id}",
                    file_path=entity.file_path,
                    type=SearchItemType.RELATION,
                    metadata={
                        "from_id": rel.from_id,
                        "to_id": rel.to_id,
                        "created_at": rel.created_at.isoformat(),
                        "updated_at": rel.updated_at.isoformat()
                    }
                )
    async def _do_index(
        self,
        id: int,
        title: str,
        content: str,
        permalink: str,
        file_path: str,
        type: SearchItemType,
        metadata: dict,
    ) -> None:
        """Actually perform the indexing."""
        await self.repository.index_item(
            id=id,
            title=title,
            content=content,
            permalink=permalink,
            file_path=file_path,
            type=type,
            metadata=metadata,
        )

    async def delete_by_permalink(self, path_id: str):
        """Delete an item from the search index."""
        await self.repository.delete_by_permalink(path_id)
