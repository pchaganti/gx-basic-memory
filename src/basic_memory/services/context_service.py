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
        max_depth: int = 2,
        since: Optional[datetime] = None,
    ):
        """Find items connected through relations.
        
        This uses a recursive CTE to traverse the knowledge graph:
        1. Start from a set of seed items (any type)
        2. Find all paths through relations in a single traversal
        3. Collect observations for any entities found
        4. Group by item to take shortest path to each
        
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
        date_filter = ""
        if since:
            date_filter = f"AND si.created_at >= {since.timestamp()}" #TODO fix date compare

        query = text(f"""
            WITH RECURSIVE context_graph AS (
                -- Base case: Starting points
                -- These can be entities, relations, or observations
                -- Each gets depth 0 and its own id as root_id
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
                WHERE (type, id) IN (VALUES {values})

                UNION ALL

                -- Relations and connected entities in a single traversal step
                -- This ensures we always take the shortest path to each item
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
                JOIN search_index si ON (
                    -- Forward relations (A -> B)
                    (si.from_id = cg.id AND si.type = 'relation')
                    OR 
                    -- Backward relations (B -> A)
                    (si.to_id = cg.id AND si.type = 'relation')
                    OR
                    -- Entities connected by relations we've found
                    -- Note: entity connection only happens after we find a relation
                    (cg.type = 'relation' AND si.type = 'entity' AND 
                     (si.id = cg.to_id OR si.id = cg.from_id))
                )
                WHERE cg.depth < {max_depth}
                {date_filter}

                UNION ALL

                -- Observations for any entities we've found
                -- These attach to entities but don't continue the traversal
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
                WHERE si.type = 'observation'
                AND cg.depth < {max_depth}
                {date_filter}
            )
            -- Take the shortest path to each item
            -- Items can be reached multiple ways, but we only want
            -- to return each one once at its minimum depth from any root
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
                min(depth) as depth,
                root_id,
                created_at
            FROM context_graph
            GROUP BY type, id, title, permalink, from_id, to_id, 
                     relation_type, category, entity_id, content, 
                     root_id, created_at
            ORDER BY type, id, depth ASC
        """)

        results = await self.search_repository.execute_query(query)
        return results.all()