"""Repository for document operations."""

from typing import Optional, Sequence, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from basic_memory.models import Document
from basic_memory.repository.repository import Repository


class DocumentRepository(Repository[Document]):
    """Repository for managing documents in the database."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        super().__init__(session_maker, Document)

    async def find_by_path(self, path: str) -> Optional[Document]:
        """Find a document by its path."""
        query = select(Document).where(Document.path == path)
        return await self.find_one(query)

    async def find_by_checksum(self, checksum: str) -> Sequence[Document]:
        """Find all documents with a given checksum."""
        async with self.session_maker() as session:
            result = await session.execute(
                select(Document).where(Document.checksum == checksum)
            )
            return result.scalars().all()

    async def find_changed(self, checksums: dict[str, str]) -> List[Document]:
        """
        Find documents that have changed based on their checksums.
        
        Args:
            checksums: Dict mapping paths to their current checksums
            
        Returns:
            List of documents whose checksums don't match (excluding untracked files)
        """
        changed = []
        for path, checksum in checksums.items():
            doc = await self.find_by_path(path)
            if doc and doc.checksum != checksum:  # Only include tracked files that changed
                changed.append(doc)
        return changed