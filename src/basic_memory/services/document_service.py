"""Service for managing documents in the system."""

import hashlib
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, Sequence

import yaml
from icecream import ic
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

    async def ensure_parent_directory(self, path: Path) -> None:
        """
        Ensure parent directory exists and is writable.

        Args:
            path: Path to check

        Raises:
            DocumentWriteError: If directory cannot be created or is not writable
        """
        parent = path.parent
        try:
            if not parent.exists():
                parent.mkdir(parents=True)

            # Verify we can write to it
            test_file = parent / ".write_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise DocumentWriteError(f"Directory not writable: {parent}: {e}")

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

    async def list_documents(self) -> Sequence[Document]:
        """List all documents in the database."""
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

        # Ensure parent directories exist and are writable
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
            ic(doc)
            return doc

        except Exception as e:
            # Clean up on any failure
            if "doc" in locals():  # DB record was created
                await self.repository.delete(doc.id)
            file_path.unlink(missing_ok=True)
            raise DocumentWriteError(f"Failed to create document: {e}")

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
            update_data["doc_metadata"] = metadata

        updated_document = await self.repository.update(doc.id, update_data)
        assert updated_document is not None, f"Could not update document {doc.id}"
        return updated_document

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
