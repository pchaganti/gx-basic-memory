"""Repository for search operations."""

import json
from typing import List, Optional

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
        """Search across all indexed content."""
        conditions = []
        params = {}

        # Handle text search
        if query.text:
            conditions.append(f"content MATCH '{query.text}'")

        # Handle type filter
        if query.types:
            # Get string values from enums
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
                permalink,
                file_path,
                type,
                metadata,
                bm25(search_index) as score
            FROM search_index 
            WHERE {where_clause}
            ORDER BY score DESC
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
                    type=SearchItemType(row.type),  # Convert string to enum
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
        type: SearchItemType,  # Now accepts enum
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
                        content, permalink, file_path, type, metadata
                    ) VALUES (
                        :content, :permalink, :file_path, :type, :metadata
                    )
                """),
                {
                    "content": content,
                    "permalink": permalink,
                    "file_path": file_path,
                    "type": type.value,  # Store the string value
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
