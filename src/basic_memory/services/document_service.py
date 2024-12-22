"""Service for managing documents in the system."""

import hashlib
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import yaml
from loguru import logger
from sqlalchemy import select

from basic_memory.models import Document
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.services.service import BaseService


class DocumentError(Exception):
    """Base exception for document operations."""
    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a document doesn't exist."""
    pass


class DocumentWriteError(DocumentError):
    """Raised when document file operations fail."""
    pass


class DocumentService(BaseService[DocumentRepository]):
    """
    Service for managing documents and their metadata.

    Handles both file operations and database tracking, keeping
    them in sync. The filesystem is the source of truth.
    """

    def __init__(self, document_repository: DocumentRepository):
        super().__init__(document_repository)

    async def compute_checksum(self, content: str) -> str:
        """Compute SHA-256 checksum of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def ensure_parent_directory(self, path: Path) -> None:
        """
        Ensure parent directory exists.

        Args:
            path: Path to check

        Raises:
            DocumentWriteError: If directory cannot be created
        """
        parent = path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise DocumentWriteError(f"Failed to create directory: {parent}: {e}")

    async def add_frontmatter(
        self, content: str, doc_id: int, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add frontmatter to document content."""
        # Generate frontmatter with timestamps
        now = datetime.now(UTC).isoformat()
        frontmatter = {"id": doc_id, "created": now, "modified": now}
        if metadata:
            frontmatter.update(metadata)

        yaml_fm = yaml.dump(frontmatter, sort_keys=False)
        return f"---\n{yaml_fm}---\n\n{content}"

    async def list_documents(self) -> List[Document]:
        """List all documents."""
        return await self.repository.find_all()

    async def create_document(
        self, path: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Create a new document.

        Args:
            path: Path where to create the document
            content: Document content
            metadata: Optional metadata to store

        Returns:
            Created document record

        Raises:
            DocumentWriteError: If file cannot be written
        """
        logger.debug(f"Creating document at {path}")

        # Ensure parent directories exist
        file_path = Path(path)
        await self.ensure_parent_directory(file_path)

        try:
            # 1. Create initial DB record to get ID
            doc = await self.repository.create({"path": str(path), "doc_metadata": metadata})

            # 2. Add frontmatter with DB-generated ID
            content_with_frontmatter = await self.add_frontmatter(content, doc.id, metadata)

            # 3. Write complete file
            file_path.write_text(content_with_frontmatter)

            # 4. Update DB with checksum to mark completion
            checksum = await self.compute_checksum(content_with_frontmatter)
            doc = await self.repository.update(doc.id, {"checksum": checksum})
            return doc

        except Exception as e:
            # Clean up on any failure
            if "doc" in locals():  # DB record was created
                await self.repository.delete(doc.id)
            file_path.unlink(missing_ok=True)
            raise DocumentWriteError(f"Failed to create document: {e}")

    async def read_document_by_id(self, id: int) -> Tuple[Document, str]:
        """
        Read a document and its content by ID.
        
        Args:
            id: Document ID
            
        Returns:
            Tuple of (document record, content)
            
        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentError: If file read fails
        """
        logger.debug(f"Reading document with ID {id}")
        
        # Get document record
        query = select(Document).where(Document.id == id)
        doc = await self.repository.find_one(query)
        if not doc:
            raise DocumentNotFoundError(f"Document not found: {id}")
            
        # Read content since file is source of truth
        try:
            file_path = Path(doc.path)
            content = file_path.read_text()
            return doc, content
        except Exception as e:
            raise DocumentError(f"Failed to read document {id}: {e}")

    async def update_document_by_id(
        self, id: int, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Update a document using its ID.

        Args:
            id: Document ID
            content: New content
            metadata: Optional new metadata

        Returns:
            Updated document record

        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentWriteError: If update fails
        """
        logger.debug(f"Updating document with ID: {id}")

        # Find document first
        query = select(Document).where(Document.id == id)
        document = await self.repository.find_one(query)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {id}")
            
        # Add frontmatter with metadata
        content_with_frontmatter = await self.add_frontmatter(content, id, metadata)

        # Write new content first
        try:
            file_path = Path(document.path)
            file_path.write_text(content_with_frontmatter)
        except Exception as e:
            raise DocumentWriteError(f"Failed to write document: {e}")

        # Update DB record
        checksum = await self.compute_checksum(content_with_frontmatter)
        update_data = {"checksum": checksum}
        if metadata is not None:
            update_data["doc_metadata"] = metadata

        updated_document = await self.repository.update(id, update_data)
        assert updated_document is not None, f"Could not update document {id}"
        return updated_document

    async def delete_document_by_id(self, id: int) -> None:
        """
        Delete a document by ID.
        
        Args:
            id: Document ID
            
        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentWriteError: If deletion fails
        """
        logger.debug(f"Deleting document with ID {id}")
        
        # Get document record first
        query = select(Document).where(Document.id == id)
        doc = await self.repository.find_one(query)
        if not doc:
            raise DocumentNotFoundError(f"Document not found: {id}")
        
        # Delete file first since it's source of truth
        try:
            file_path = Path(doc.path)
            file_path.unlink(missing_ok=True)
        except Exception as e:
            raise DocumentWriteError(f"Failed to delete document {id}: {e}")
            
        # Delete database record
        await self.repository.delete(doc.id)