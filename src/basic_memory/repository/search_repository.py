"""Repository for search operations."""

import json
from typing import List, Optional, Any, Dict

from loguru import logger
from sqlalchemy import text, Executable, Result
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory import db
from basic_memory.models.search import CREATE_SEARCH_INDEX
from basic_memory.repository.repository import Repository
from basic_memory.schemas.search import SearchQuery, SearchResult, SearchItemType


class SearchRepository:
    """Repository for search index operations."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def init_search_index(self):
        """Create or recreate the search index."""
        async with db.scoped_session(self.session_maker) as session:
            await session.execute(CREATE_SEARCH_INDEX)
            await session.commit()

    def _quote_search_term(self, term: str) -> str:
        """Add quotes if term contains special characters."""
        if any(c in term for c in "/-"):
            return f'"{term}"'
        return term

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search across all indexed content with fuzzy matching."""
        conditions = []
        params = {}

        # Handle text search
        if query.text:
            search_text = self._quote_search_term(query.text.lower().strip())
            params["text"] = f"{search_text}*"
            conditions.append("(title MATCH :text OR content MATCH :text)")

        # Handle permalink search
        if query.permalink:
            params["permalink"] = query.permalink
            conditions.append("permalink = :permalink")
            
        elif query.permalink_pattern:
            # Use LIKE for pattern matching - convert * to %
            sql_pattern = query.permalink_pattern.replace('*', '%')
            params["permalink_pattern"] = sql_pattern
            conditions.append("permalink LIKE :permalink_pattern")

        # Handle type filter
        if query.types:
            type_list = ", ".join(f"'{t.value}'" for t in query.types)
            conditions.append(f"type IN ({type_list})")

        # Handle entity type filter
        if query.entity_types:
            entity_type_list = ", ".join(f"'{t}'" for t in query.entity_types)
            conditions.append(f"json_extract(metadata, '$.entity_type') IN ({entity_type_list})")

        # Handle date filter
        if query.after_date:
            params["after_date"] = query.after_date
            conditions.append("json_extract(metadata, '$.created_at') > :after_date")

        # Build WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT 
                id, 
                permalink,
                file_path,
                type,
                metadata,
                from_id,
                to_id,
                relation_type,
                entity_id,
                category,
                bm25(search_index) as score
            FROM search_index 
            WHERE {where_clause}
            ORDER BY score ASC
        """

        logger.debug(f"Search query: {sql}")
        logger.debug(f"Search params: {params}")

        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                SearchResult(
                    id=row.id,
                    permalink=row.permalink,
                    file_path=row.file_path,
                    type=SearchItemType(row.type),
                    score=row.score,
                    metadata=json.loads(row.metadata),
                    from_id=row.from_id,
                    to_id=row.to_id,
                    relation_type=row.relation_type,
                    entity_id=row.entity_id,
                    category=row.category
                )
                for row in rows
            ]

    async def index_item(
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
    ):
        """Index or update a single item."""
        async with db.scoped_session(self.session_maker) as session:
            # Delete existing record if any
            await session.execute(
                text("DELETE FROM search_index WHERE permalink = :permalink"),
                {"permalink": permalink},
            )

            # Insert new record
            await session.execute(
                text("""
                    INSERT INTO search_index (
                        id, title, content, permalink, file_path, type, metadata,
                        from_id, to_id, relation_type,
                        entity_id, category,
                        created_at, updated_at
                    ) VALUES (
                        :id, :title, :content, :permalink, :file_path, :type, :metadata,
                        :from_id, :to_id, :relation_type,
                        :entity_id, :category,
                        :created_at, :updated_at
                    )
                """),
                {
                    "id": id,
                    "title": title,
                    "content": content,
                    "permalink": permalink,
                    "file_path": file_path,
                    "type": type.value,
                    "metadata": json.dumps(metadata),
                    "from_id": from_id,
                    "to_id": to_id,
                    "relation_type": relation_type,
                    "entity_id": entity_id,
                    "category": category,
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at")
                },
            )
            logger.debug(f"indexed {permalink}")
            await session.commit()

    async def delete_by_permalink(self, permalink: str):
        """Delete an item from the search index."""
        async with db.scoped_session(self.session_maker) as session:
            await session.execute(
                text("DELETE FROM search_index WHERE permalink = :permalink"),
                {"permalink": permalink},
            )
            await session.commit()

    async def execute_query(
        self, 
        query: Executable, 
        params: Optional[Dict[str, Any]] = None, 
        use_query_options:bool = True
    ) -> Result[Any]:
        """Execute a query asynchronously."""
        logger.debug(f"Executing query: {query}")
        async with db.scoped_session(self.session_maker) as session:
            if params:
                result = await session.execute(query, params)
            else:
                result = await session.execute(query)
            logger.debug("Query executed successfully")
            return result