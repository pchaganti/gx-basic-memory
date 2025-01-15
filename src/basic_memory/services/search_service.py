"""Service for search operations."""

from typing import List, Optional, Set

from fastapi import BackgroundTasks
from loguru import logger

from basic_memory.models import Entity
from basic_memory.repository import EntityRepository
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.schemas.search import SearchQuery, SearchResult, SearchItemType


class SearchService:
    """Service for search operations.
    
    Supports three primary search modes:
    1. Exact permalink lookup
    2. Pattern matching with * (e.g., 'specs/*')
    3. Full-text search across title/content
    """

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
        self, 
        query: SearchQuery, 
        context: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search across all indexed content.
        
        Supports three modes:
        1. Exact permalink: finds direct matches for a specific path
        2. Pattern match: handles * wildcards in paths
        3. Text search: full-text search across title/content
        """
        logger.debug(f"Searching with query: {query}")
        
        # Determine search mode based on provided parameters
        if query.permalink:
            # Exact permalink lookup
            results = await self.repository.search(
                SearchQuery(permalink=query.permalink)
            )
        elif query.permalink_pattern:
            # Pattern matching with *
            results = await self.repository.search(
                SearchQuery(permalink_pattern=query.permalink_pattern)
            )
        elif query.text:
            # Full-text search
            results = await self.repository.search(
                SearchQuery(text=query.text)
            )
        else:
            return []  # No search criteria provided
            
        # Apply any filters
        results = [
            r for r in results
            if (not query.types or r.type in query.types) and
               (not query.entity_types or
                (r.type == SearchItemType.ENTITY and 
                 r.metadata.get('entity_type') in query.entity_types))
        ]
        
        return results

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
        """Index an entity and all its observations and relations.
        
        Indexing structure:
        1. Entities
           - permalink: direct from entity (e.g., "specs/search")
           - file_path: physical file location
        
        2. Observations
           - permalink: entity permalink + /observations/id (e.g., "specs/search/observations/123")
           - file_path: parent entity's file (where observation is defined)
        
        3. Relations (only index outgoing relations defined in this file)
           - permalink: from_entity/relation_type/to_entity (e.g., "specs/search/implements/features/search-ui")
           - file_path: source entity's file (where relation is defined)

        Each type gets its own row in the search index with appropriate metadata.
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

        # Index each observation with synthetic permalink
        for obs in entity.observations:
            # Create synthetic permalink for the observation
            # We can construct these because observations are always
            # defined in and owned by a single entity
            observation_permalink = f"{entity.permalink}/observations/{obs.id}"
            
            # Index with parent entity's file path since that's where it's defined
            if background_tasks:
                background_tasks.add_task(
                    self._do_index,
                    id=obs.id,
                    title=f"{obs.category}: {obs.content[:50]}...",
                    content=obs.content,
                    permalink=observation_permalink,
                    file_path=entity.file_path,
                    type=SearchItemType.OBSERVATION,
                    category=obs.category,
                    entity_id=entity.id,
                    metadata={
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
                    permalink=observation_permalink,
                    file_path=entity.file_path,
                    type=SearchItemType.OBSERVATION,
                    category=obs.category,
                    entity_id=entity.id,
                    metadata={
                        "created_at": obs.created_at.isoformat(),
                        "updated_at": obs.updated_at.isoformat(),
                        "tags": obs.tags
                    }
                )

        # Only index outgoing relations (ones defined in this file)
        for rel in entity.outgoing_relations:
            # Create relation permalink showing the semantic connection:
            # source/relation_type/target
            # e.g., "specs/search/implements/features/search-ui"
            relation_permalink = f"{rel.from_entity.permalink}/{rel.relation_type}/{rel.to_entity.permalink}"
            
            # Create descriptive title showing the relationship
            relation_title = f"{rel.from_entity.title} → {rel.to_entity.title}"
            
            if background_tasks:
                background_tasks.add_task(
                    self._do_index,
                    id=rel.id,
                    title=relation_title,
                    content=rel.context or "",
                    permalink=relation_permalink,
                    file_path=entity.file_path,
                    type=SearchItemType.RELATION,
                    from_id=rel.from_id,
                    to_id=rel.to_id,
                    relation_type=rel.relation_type,
                    metadata={
                        "created_at": rel.created_at.isoformat(),
                        "updated_at": rel.updated_at.isoformat()
                    }
                )
            else:
                await self._do_index(
                    id=rel.id,
                    title=relation_title,
                    content=rel.context or "",
                    permalink=relation_permalink,
                    file_path=entity.file_path,
                    type=SearchItemType.RELATION,
                    from_id=rel.from_id,
                    to_id=rel.to_id,
                    relation_type=rel.relation_type,
                    metadata={
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
        from_id: Optional[int] = None,
        to_id: Optional[int] = None,
        relation_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        category: Optional[str] = None,
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
            from_id=from_id,
            to_id=to_id,
            relation_type=relation_type,
            entity_id=entity_id,
            category=category,
        )

    async def delete_by_permalink(self, path_id: str):
        """Delete an item from the search index."""
        await self.repository.delete_by_permalink(path_id)