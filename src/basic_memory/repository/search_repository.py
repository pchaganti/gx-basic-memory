"""Repository for search operations."""

import json
from typing import List, Optional
from pathlib import Path

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory import db
from basic_memory.models.search import CREATE_SEARCH_INDEX
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

    async def search(
        self, query: SearchQuery, context: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search across all indexed content with fuzzy matching."""
        conditions = []
        params = {}

        # Handle text search
        if query.text:
            search_text = query.text.lower().strip()
            params["text"] = f"{search_text}*"
            conditions.append("(title MATCH :text OR content MATCH :text)")

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

        # Add context-based path matching if context provided
        if context:
            context_conditions = []
            for i, path in enumerate(context):
                param_name = f"context_{i}"
                params[param_name] = f"%{Path(path).parent.as_posix()}%"
                context_conditions.append(f"file_path LIKE :{param_name}")
            if context_conditions:
                conditions.append(f"({' OR '.join(context_conditions)})")

        # Build WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT 
                permalink,
                file_path,
                type,
                metadata,
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
                    permalink=row.permalink,
                    file_path=row.file_path,
                    type=SearchItemType(row.type),
                    score=row.score,
                    metadata=json.loads(row.metadata),
                )
                for row in rows
            ]

    async def index_item(
        self,
        title: str,
        content: str,
        permalink: str,
        file_path: str,
        type: SearchItemType,
        metadata: dict,
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
                        title, content, permalink, file_path, type, metadata
                    ) VALUES (
                        :title, :content, :permalink, :file_path, :type, :metadata
                    )
                """),
                {
                    "title": title,
                    "content": content,
                    "permalink": permalink,
                    "file_path": file_path,
                    "type": type.value,
                    "metadata": json.dumps(metadata),
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
