"""Service for managing documents in the system."""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

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
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file first
        try:
            file_path.write_text(content)
        except Exception as e:
            raise DocumentWriteError(f"Failed to write document file: {e}")

        # After file is written, create database record
        try:
            checksum = await self.compute_checksum(content)
            doc = await self.repository.create(
                {"path": str(path), "checksum": checksum, "doc_metadata": metadata}
            )
            return doc
        except Exception:
            # If database operation fails, clean up the file
            file_path.unlink(missing_ok=True)
            raise

    async def read_document(self, path: str) -> tuple[Document, str]:
        """
        Read a document and its content.

        Args:
            path: Path to the document

        Returns:
            Tuple of (document record, content)

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        logger.debug(f"Reading document at {path}")

        # Check if file exists
        file_path = Path(path)
        if not file_path.exists():
            raise DocumentNotFoundError(f"Document not found: {path}")

        # Read content first since file is source of truth
        try:
            content = file_path.read_text()
        except Exception as e:
            raise DocumentError(f"Failed to read document: {e}")

        # Get document record
        doc = await self.repository.find_by_path(str(path))
        if not doc:
            # File exists but no DB record - create one
            checksum = await self.compute_checksum(content)
            doc = await self.repository.create({"path": str(path), "checksum": checksum})

        return doc, content

    async def update_document(
        self, path: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Update an existing document.

        Args:
            path: Path to the document
            content: New content
            metadata: Optional new metadata

        Returns:
            Updated document record

        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentWriteError: If update fails
        """
        logger.debug(f"Updating document at {path}")

        # Verify file exists
        file_path = Path(path)
        if not file_path.exists():
            raise DocumentNotFoundError(f"Document not found: {path}")

        # Write new content first
        try:
            file_path.write_text(content)
        except Exception as e:
            raise DocumentWriteError(f"Failed to write document: {e}")

        # Update database record
        doc = await self.repository.find_by_path(str(path))
        if not doc:
            # File exists but no DB record - create one
            checksum = await self.compute_checksum(content)
            return await self.repository.create(
                {"path": str(path), "checksum": checksum, "doc_metadata": metadata}
            )

        # Update existing record
        checksum = await self.compute_checksum(content)
        update_data = {"checksum": checksum}
        if metadata is not None:
            update_data["doc_metadata"] = metadata  # pyright: ignore [reportArgumentType]

        return await self.repository.update(doc.id, update_data)

    async def delete_document(self, path: str) -> None:
        """
        Delete a document.

        Args:
            path: Path to the document

        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentWriteError: If deletion fails
        """
        logger.debug(f"Deleting document at {path}")

        # Verify file exists
        file_path = Path(path)
        if not file_path.exists():
            raise DocumentNotFoundError(f"Document not found: {path}")

        # Delete file first
        try:
            file_path.unlink()
        except Exception as e:
            raise DocumentWriteError(f"Failed to delete document: {e}")

        # Delete database record if it exists
        doc = await self.repository.find_by_path(str(path))
        if doc:
            await self.repository.delete(doc.id)
