"""Service for managing documents in the system."""

from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Sequence

from loguru import logger

from basic_memory.models import Document
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.services.service import BaseService
from basic_memory.services.file_service import FileService
from basic_memory.services.exceptions import FileOperationError


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

    def __init__(
        self,
        document_repository: DocumentRepository,
        documents_path: Path,
        file_service: FileService,
    ):
        super().__init__(document_repository)
        self.documents_base_path = documents_path
        self.file_service = file_service

    def get_document_path(self, path_id: str) -> Path:
        """Get full filesystem path for a document."""
        doc_path = Path(path_id)
        if doc_path.is_absolute():
            raise DocumentError(f"Document path {path_id} must be relative")

        document_path = self.documents_base_path / path_id
        logger.debug(f"Document path: '{path_id}' file_path: {document_path}")
        return document_path

    async def list_documents(self) -> Sequence[Document]:
        """List all documents."""
        return await self.repository.find_all()

    async def create_document(
        self,
        path_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        Create a new document.

        Args:
            path_id: Path where to create the document
            content: Document content
            metadata: Optional metadata to store

        Returns:
            Created document record

        Raises:
            DocumentWriteError: If file cannot be written
        """
        logger.debug(f"Creating document path_id: {path_id}")

        file_path = self.get_document_path(path_id)
        try:
            # Prepare frontmatter
            now = datetime.now(UTC).isoformat()
            frontmatter = {
                "id": path_id,
                "created": now,
                "modified": now
            }
            if metadata:
                frontmatter.update(metadata)

            # Let FileService handle the write with frontmatter
            checksum = await self.file_service.write_with_frontmatter(
                path=file_path,
                content=content,
                frontmatter=frontmatter
            )

            # Create DB record
            document = await self.repository.create({
                "path_id": path_id,
                "file_path": path_id,
                "checksum": checksum,
                "doc_metadata": metadata
            })

            return document

        except FileOperationError as e:
            raise DocumentWriteError(f"Failed to create document: {e}")
        except Exception as e:
            # Clean up on any failure
            await self.file_service.delete_file(file_path)
            raise DocumentWriteError(f"Failed to create document: {e}")

    async def read_document_by_path_id(self, path_id: str) -> Tuple[Document, str]:
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
        document = await self.repository.find_by_path_id(path_id)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {path_id}")

        try:
            # Read content using FileService
            file_path = self.get_document_path(document.file_path)
            content, _ = await self.file_service.read_file(file_path)
            return document, content

        except FileOperationError as e:
            raise DocumentError(f"Failed to read document {path_id}: {e}")

    async def update_document_by_path_id(
        self,
        path_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
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
        document = await self.repository.find_by_path_id(path_id)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {path_id}")

        try:
            # Read existing content to preserve frontmatter
            file_path = self.get_document_path(document.file_path)
            old_content, _ = await self.file_service.read_file(file_path)
            try:
                existing_frontmatter = await self.file_service.parse_frontmatter(old_content)
            except:
                # If we can't parse existing frontmatter, start fresh
                existing_frontmatter = {
                    "id": path_id,
                    "created": datetime.now(UTC).isoformat(),
                }

            # Update frontmatter
            now = datetime.now(UTC).isoformat()
            frontmatter = {
                **existing_frontmatter,
                "modified": now,
            }
            if metadata:
                frontmatter.update(metadata)

            # Update file using FileService
            checksum = await self.file_service.write_with_frontmatter(
                path=file_path,
                content=content,
                frontmatter=frontmatter
            )

            # Update DB record
            update_data = {"checksum": checksum}
            if metadata is not None:
                update_data["doc_metadata"] = metadata

            updated_document = await self.repository.update(document.id, update_data)
            return updated_document

        except FileOperationError as e:
            raise DocumentWriteError(f"Failed to update document: {e}")

    async def delete_document_by_path_id(self, path_id: str) -> None:
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
        document = await self.repository.find_by_path_id(path_id)
        if not document:
            raise DocumentNotFoundError(f"Document not found: {path_id}")

        try:
            # Delete file using FileService
            file_path = self.get_document_path(document.path_id)
            await self.file_service.delete_file(file_path)

            # Delete database record
            await self.repository.delete(document.id)

        except FileOperationError as e:
            raise DocumentWriteError(f"Failed to delete document {path_id}: {e}")
