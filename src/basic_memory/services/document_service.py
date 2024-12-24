"""Service for managing documents in the system."""

import hashlib
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Sequence

import yaml
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

    def __init__(self, document_repository: DocumentRepository, documents_path: Path):
        super().__init__(document_repository)
        self.documents_base_path = documents_path

    def get_document_path(self, path: str) -> Path:
        doc_path = Path(path)
        if doc_path.is_absolute():
            raise DocumentError(f"Document path {path} must be relative")

        document_path = Path(self.documents_base_path / path)
        logger.debug(f"Document path: '{path}' file_path: {document_path}")
        return document_path

    async def compute_checksum(self, content: str) -> str:
        """Compute SHA-256 checksum of content."""
        try:
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception as e:  # pragma: no cover
            # This would only happen if encode() fails or sha256 isn't available
            logger.error(f"Failed to compute checksum: {e}")
            raise DocumentError(f"Failed to compute checksum: {e}")

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
        except Exception as e:  # pragma: no cover
            # This is covered by create_document tests, but not directly
            raise DocumentWriteError(f"Failed to create directory: {parent}: {e}")

    async def add_frontmatter(
        self, content: str, path_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add frontmatter to document content."""
        # Generate frontmatter with timestamps
        now = datetime.now(UTC).isoformat()
        frontmatter = {"id": path_id, "created": now, "modified": now}
        if metadata:
            frontmatter.update(metadata)

        yaml_fm = yaml.dump(frontmatter, sort_keys=False)
        return f"---\n{yaml_fm}---\n\n{content}"

    async def list_documents(self) -> Sequence[Document]:
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
        logger.debug(f"Creating document at path: {path}")

        # Ensure parent directories exist
        file_path = self.get_document_path(path)
        await self.ensure_parent_directory(file_path)

        # db reference
        document = None
        try:
            # 1. Create initial DB record to get ID
            document = await self.repository.create({"path": str(path), "doc_metadata": metadata})

            # 2. Add frontmatter with DB-generated ID
            content_with_frontmatter = await self.add_frontmatter(content, path, metadata)

            # 3. Write complete file
            file_path.write_text(content_with_frontmatter)

            # 4. Update DB with checksum to mark completion
            checksum = await self.compute_checksum(content_with_frontmatter)
            document = await self.repository.update(document.id, {"checksum": checksum})

            # If either update failed but didn't raise
            if not document:  # pragma: no cover
                raise DocumentError("Failed to update document after writing")

            return document

        except Exception as e:
            # Clean up on any failure
            if document:  # DB record was created
                await self.repository.delete(document.id)
            file_path.unlink(missing_ok=True)
            raise DocumentWriteError(f"Failed to create document: {e}")

    async def read_document_by_path(self, path_id: str) -> Tuple[Document, str]:
        """
        Read a document and its content by PathId.

        Args:
            path_id: Document PathId

        Returns:
            Tuple of (document record, content)

        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentError: If file read fails
        """
        logger.debug(f"Reading document with path_id: {path_id}")

        # Get document record
        document = await self.repository.find_by_path(path_id)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {path_id}")

        # Read content since file is source of truth
        file_path = self.get_document_path(document.path)
        try:
            content = file_path.read_text()
            return document, content
        except Exception as e:
            raise DocumentError(f"Failed to read document {path_id}: {e} at path {file_path}")

    async def update_document_by_path(
        self, path_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Update a document using its PathId.

        Args:
            path_id: Document PathId
            content: New content
            metadata: Optional new metadata

        Returns:
            Updated document record

        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentWriteError: If update fails
        """
        logger.debug(f"Updating document with ID: {path_id}")

        # Find document first
        document = await self.repository.find_by_path(path_id)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {path_id}")

        # Add frontmatter with metadata
        content_with_frontmatter = await self.add_frontmatter(content, path_id, metadata)

        # Write new content first
        try:
            file_path = self.get_document_path(document.path)
            file_path.write_text(content_with_frontmatter)
        except Exception as e:
            raise DocumentWriteError(f"Failed to write document: {e}")

        # Update DB record
        checksum = await self.compute_checksum(content_with_frontmatter)
        update_data = {"checksum": checksum}
        if metadata is not None:
            update_data["doc_metadata"] = metadata  # pyright: ignore [reportArgumentType]

        updated_document = await self.repository.update(document.id, update_data)

        # This would only happen if DB lost connection between find and update
        if not updated_document:  # pragma: no cover
            raise DocumentError(f"Could not update document {path_id}")

        return updated_document

    async def delete_document_by_path(self, path_id: str) -> None:
        """
        Delete a document by PathId.

        Args:
            path_id: Document PathId

        Raises:
            DocumentNotFoundError: If document doesn't exist
            DocumentWriteError: If deletion fails
        """
        logger.debug(f"Deleting document with path_id {path_id}")

        # Get document record first
        document = await self.repository.find_by_path(path_id)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {path_id}")

        # Delete file first since it's source of truth
        try:
            file_path = self.get_document_path(document.path)
            file_path.unlink(missing_ok=True)
        except Exception as e:
            raise DocumentWriteError(f"Failed to delete document {path_id}: {e}")

        # Delete database record
        await self.repository.delete(document.id)
