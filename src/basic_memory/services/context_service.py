"""Service for building rich context from the knowledge graph."""

from datetime import datetime, timedelta
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
        """Build rich context from a memory:// URI."""
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
            max_depth=depth,
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
        max_depth: int = 2,
        since: Optional[datetime] = None,
    ):
        """Find items connected through relations.
        
        Args:
            type_id_pairs: List of (type, id) tuples to start from
            max_depth: How many relation steps to traverse
            since: Only include items modified since this time
        """
        if not type_id_pairs:
            return []
            
        logger.debug(f"Finding connected items for {type_id_pairs} with depth {max_depth}")

        # Build the VALUES clause for our seed items
        values = ", ".join([f"('{t}', {i})" for t, i in type_id_pairs])

        # Build date condition for timeframe filtering
        date_filter = f""
        if since:
            date_filter = f"AND created_at >= '{since.isoformat()}'"

        # Debug: Check what's in the search index
        debug_query = text("""
            SELECT type, id, from_id, to_id, relation_type 
            FROM search_index 
            ORDER BY type, id
        """)
        debug_results = await self.search_repository.execute_query(debug_query)
        logger.debug("Current search index contents:")
        for r in debug_results:
            if r.type == "relation":
                logger.debug(f"Relation {r.id}: from={r.from_id} to={r.to_id} type={r.relation_type}")
            else:
                logger.debug(f"{r.type} {r.id}")

        query = text(f"""
            WITH RECURSIVE context_graph AS (
                -- Base case: seed items
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
                FROM search_index base
                WHERE (type, id) IN (VALUES {values})
                {date_filter}

                UNION 

                -- Find all connected items (relations + entities) at each depth
                SELECT
                    related.id,
                    related.type,
                    related.title,
                    related.permalink,
                    related.from_id,
                    related.to_id,
                    related.relation_type,
                    related.category,
                    related.entity_id,
                    related.content,
                    cg.depth + 1,
                    cg.root_id,
                    related.created_at
                FROM context_graph cg
                INNER JOIN search_index r1 ON (
                    -- First find the relations
                    cg.type = 'entity' AND 
                    r1.type = 'relation' AND 
                    (r1.from_id = cg.id OR r1.to_id = cg.id)
                    {date_filter.replace('created_at', 'r1.created_at')}
                )
                -- Then join to ALL related items at the same depth 
                LEFT JOIN search_index related ON (
                    -- The found relation 
                    related.id = r1.id
                    OR
                    -- The entity it connects to
                    (related.type = 'entity' AND 
                     (related.id = r1.from_id OR related.id = r1.to_id))
                    OR
                    -- Any observations that are relevant
                    (related.type = 'observation' AND 
                     (related.entity_id = r1.from_id OR related.entity_id = r1.to_id))
                )
                WHERE cg.depth < {max_depth}
                {date_filter.replace('created_at', 'related.created_at')}
            )
            -- Select shortest path to each item
            SELECT DISTINCT 
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
                MIN(depth) as depth,
                root_id,
                created_at
            FROM context_graph
            GROUP BY
                type, id, title, permalink, from_id, to_id,
                relation_type, category, entity_id, content,
                root_id, created_at
            ORDER BY depth, type
        """)

        results = await self.search_repository.execute_query(query)
        return results.all()