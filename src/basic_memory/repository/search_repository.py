"""Repository for search operations."""

import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory import db
from basic_memory.repository.repository import Repository
from basic_memory.schemas.search import SearchQuery, SearchResult, SearchItemType
from basic_memory.models.search import CREATE_SEARCH_INDEX


class SearchRepository():
    """Repository for search index operations."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def init_search_index(self):
        """Create or recreate the search index."""
        async with db.scoped_session(self.session_maker) as session:
            await session.execute(CREATE_SEARCH_INDEX)
            await session.commit()

    async def search(
        self,
        query: SearchQuery,
        context: Optional[List[str]] = None
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
            conditions.append(
                f"json_extract(metadata, '$.entity_type') IN ({entity_type_list})"
            )

        # Handle date filter
        if query.after_date:
            params["after_date"] = query.after_date.isoformat()
            conditions.append(
                "json_extract(metadata, '$.created_at') > :after_date"
            )

        # Build WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT 
                path_id,
                file_path,
                type,
                metadata,
                bm25(search_index) as score
            FROM search_index 
            WHERE {where_clause}
            ORDER BY score DESC
        """

        async with db.scoped_session(self.session_maker) as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                SearchResult(
                    path_id=row.path_id,
                    file_path=row.file_path,
                    type=SearchItemType(row.type),  # Convert string to enum
                    score=row.score,
                    metadata=json.loads(row.metadata)
                )
                for row in rows
            ]

    async def index_item(
        self,
        content: str,
        path_id: str,
        file_path: str,
        type: SearchItemType,  # Now accepts enum
        metadata: dict
    ):
        """Index or update a single item."""
        async with db.scoped_session(self.session_maker) as session:
            # Delete existing record if any
            await session.execute(
                text("DELETE FROM search_index WHERE path_id = :path_id"),
                {"path_id": path_id}
            )

            # Insert new record
            await session.execute(
                text("""
                    INSERT INTO search_index (
                        content, path_id, file_path, type, metadata
                    ) VALUES (
                        :content, :path_id, :file_path, :type, :metadata
                    )
                """),
                {
                    "content": content,
                    "path_id": path_id,
                    "file_path": file_path,
                    "type": type.value,  # Store the string value
                    "metadata": json.dumps(metadata)
                }
            )
            await session.commit()

    async def delete_by_path(self, path_id: str):
        """Delete an item from the search index."""
        async with db.scoped_session(self.session_maker) as session:
            await session.execute(
                text("DELETE FROM search_index WHERE path_id = :path_id"),
                {"path_id": path_id}
            )
            await session.commit()