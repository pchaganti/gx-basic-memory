"""Service for building rich context from the knowledge graph."""

from datetime import datetime, UTC
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import text
from loguru import logger

from basic_memory.repository.search_repository import SearchRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas.memory_url import MemoryUrl
from basic_memory.schemas.search import SearchItemType


class ContextService:
    """Service for building rich context from memory:// URIs."""
    
    def __init__(
        self,
        search_repository: SearchRepository,
        entity_repository: EntityRepository,
    ):
        self.search_repository = search_repository
        self.entity_repository = entity_repository

    async def build_context(
        self,
        uri: str,
        depth: int = 2,
        since: Optional[datetime] = None,
    ):
        """Build rich context from a memory:// URI.
        
        Args:
            uri: memory:// URI to build context from
            depth: How many relation steps to traverse (default: 2)
            since: Only include items modified since this time
        """
        logger.debug(f"Building context for URI {uri}")
        
        # Parse the URI
        memory_url = MemoryUrl.parse(uri)
        
        # Handle different URL types
        if memory_url.pattern:
            # Pattern matching (*)
            primary = await self.find_by_pattern(memory_url.pattern)
        elif memory_url.fuzzy:
            # Fuzzy search (~)
            primary = await self.find_by_fuzzy(memory_url.fuzzy)
        elif memory_url.params.get("type") == "related":
            # Related content
            primary = await self.find_related(memory_url.params["target"])
        else:
            # Direct permalink lookup
            primary = await self.find_by_permalink(memory_url.relative_path())

        # Get type_id pairs from primary results
        type_id_pairs = [(r.type, r.id) for r in primary] if primary else []

        # Find connected entities through relations
        related = await self.find_connected(
            type_id_pairs,
            depth=depth,
            since=since
        )
        
        return {
            "primary": primary,
            "related": related
        }

    async def find_by_pattern(self, pattern: str):
        """Find entities matching a glob pattern."""
        # TODO: Implement pattern matching
        return []

    async def find_by_fuzzy(self, search_terms: str):
        """Find entities using fuzzy text search."""
        # TODO: Implement fuzzy search
        return []

    async def find_related(self, permalink: str):
        """Find entities related to a given permalink."""
        # TODO: Implement related content search
        return []

    async def find_by_permalink(self, permalink: str):
        """Find an entity by exact permalink."""
        # TODO: Implement direct permalink lookup
        return []

    async def find_connected(
        self,
        type_id_pairs: List[Tuple[str, int]],
        depth: int = 2,
        since: Optional[datetime] = None,
    ):
        """Find items connected through relations.
        
        Args:
            type_id_pairs: List of (type, id) tuples to start from
            depth: How many relation steps to traverse
            since: Only include items modified since this time
        """
        if not type_id_pairs:
            return []
            
        logger.debug(f"Finding connected items for {type_id_pairs} with depth {depth}")

        # Build date condition
        date_filter = ""
        if since:
            date_filter = "AND si.created_at >= :since"

        # Build VALUES clause for type_id pairs
        value_list = []
        params = {}
        for i, (type_, id_) in enumerate(type_id_pairs):
            value_list.append(f"(:type_{i}, :id_{i})")
            params[f"type_{i}"] = type_
            params[f"id_{i}"] = id_
        values_clause = f"({','.join(value_list)})"

        query = text(f"""
            WITH RECURSIVE context_graph AS (
                -- Base case: Start with provided items
                SELECT
                    id,
                    type,
                    title,
                    permalink,
                    from_id,
                    to_id,
                    relation_type,
                    category,
                    entity_id,
                    content,
                    0 as depth,
                    id as root_id,
                    created_at
                FROM search_index
                WHERE (type, id) IN {values_clause}

                UNION ALL

                -- Forward relations
                SELECT
                    si.id,
                    si.type,
                    si.title,
                    si.permalink,
                    si.from_id,
                    si.to_id,
                    si.relation_type,
                    si.category,
                    si.entity_id,
                    si.content,
                    cg.depth + 1,
                    cg.root_id,
                    si.created_at
                FROM context_graph cg
                JOIN search_index si ON si.from_id = cg.id 
                WHERE si.type = :relation_type
                AND cg.depth < :max_depth
                {date_filter}

                UNION ALL

                -- Backward relations
                SELECT
                    si.id,
                    si.type,
                    si.title,
                    si.permalink,
                    si.from_id,
                    si.to_id,
                    si.relation_type,
                    si.category,
                    si.entity_id,
                    si.content,
                    cg.depth + 1,
                    cg.root_id,
                    si.created_at
                FROM context_graph cg
                JOIN search_index si ON si.to_id = cg.id
                WHERE si.type = :relation_type
                AND cg.depth < :max_depth
                {date_filter}

                UNION ALL

                -- Get entities on either side of relations
                SELECT
                    si.id,
                    si.type,
                    si.title,
                    si.permalink,
                    si.from_id,
                    si.to_id,
                    si.relation_type,
                    si.category,
                    si.entity_id,
                    si.content,
                    cg.depth + 1,
                    cg.root_id,
                    si.created_at
                FROM context_graph cg
                JOIN search_index si ON si.id = cg.to_id OR si.id = cg.from_id
                WHERE si.type = :entity_type
                AND cg.type = :relation_type
                AND cg.depth < :max_depth
                {date_filter}

                UNION ALL

                -- Get observations for entities
                SELECT
                    si.id,
                    si.type,
                    si.title,
                    si.permalink,
                    si.from_id,
                    si.to_id,
                    si.relation_type,
                    si.category,
                    si.entity_id,
                    si.content,
                    cg.depth + 1,
                    cg.root_id,
                    si.created_at
                FROM context_graph cg
                JOIN search_index si ON si.entity_id = cg.id
                WHERE si.type = :observation_type
                AND cg.depth < :max_depth
                {date_filter}
            )
            SELECT
                type,
                id,
                title,
                permalink,
                from_id,
                to_id,
                relation_type,
                category,
                entity_id,
                content,
                depth,
                root_id,
                created_at
            FROM context_graph
            ORDER BY type, id, depth ASC
        """)

        # Add remaining parameters
        params.update({
            "max_depth": depth,
            "since": since,
            "entity_type": SearchItemType.ENTITY.value,
            "relation_type": SearchItemType.RELATION.value,
            "observation_type": SearchItemType.OBSERVATION.value
        })

        results = await self.search_repository.execute_query(query, params)
        return results