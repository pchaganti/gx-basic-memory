"""Tests for DocumentService."""

from datetime import datetime
from pathlib import Path
from typing import Tuple

import pytest
import pytest_asyncio
import yaml
from sqlalchemy import select

from basic_memory.models import Document
from basic_memory.services.document_service import (
    DocumentNotFoundError,
    DocumentWriteError,
    DocumentError,
)


@pytest_asyncio.fixture
async def test_doc_path(document_service) -> Tuple[Path, str]:
    path_id = "test_docs/test.md"
    file_path = document_service.documents_base_path / path_id
    return file_path, path_id


@pytest.mark.asyncio
async def test_create_document_with_frontmatter(document_service, test_doc_path):
    """Test that created documents have proper frontmatter."""

    file_path, path_id = test_doc_path

    content = "# Test Document\n\nThis is a test."
    doc = await document_service.create_document(path_id, content, {"type": "test"})

    # Verify file content
    file_content = file_path.read_text()

    # Parse frontmatter

    # Split content at the second "---" marker
    _, frontmatter, doc_content = file_content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)

    # Verify frontmatter contents
    assert metadata["id"] == path_id
    assert metadata["type"] == "test"
    assert "created" in metadata
    assert "modified" in metadata

    # Verify timestamps are valid ISO format
    datetime.fromisoformat(metadata["created"])
    datetime.fromisoformat(metadata["modified"])

    # Verify original content is preserved
    assert content in doc_content

    # Verify DB record
    assert doc.path_id == path_id
    assert doc.doc_metadata == {"type": "test"}
    assert doc.checksum is not None


@pytest.mark.asyncio
async def test_create_document_cleanup_on_write_failure(document_service, test_doc_path):
    """Test that failed document creation cleans up DB record when file write fails."""

    file_path, path_id = test_doc_path

    def fail_write(self, content):
        raise PermissionError("Mock write failure")

    # Store original write_text method
    original_write_text = Path.write_text

    try:
        # Replace write_text with our failing version
        Path.write_text = fail_write

        with pytest.raises(DocumentWriteError) as exc_info:
            await document_service.create_document(path_id, "test content", {"type": "test"})

        assert "Mock write failure" in str(exc_info.value)

        # Verify DB record was cleaned up
        query = select(Document).where(Document.path_id == path_id)
        doc = await document_service.repository.find_one(query)
        assert doc is None

        # Verify no file was created
        assert not file_path.exists()

    finally:
        # Restore original write_text method
        Path.write_text = original_write_text


@pytest.mark.asyncio
async def test_read_document_by_id(document_service, test_doc_path):
    """Test reading a document by ID."""

    file_path, path_id = test_doc_path

    # Create test document
    content = "# Test Document\nTest content."
    doc = await document_service.create_document(path_id, content, {"type": "test"})

    # Read it back
    retrieved_doc, retrieved_content = await document_service.read_document_by_path_id(path_id)

    assert retrieved_doc.id == doc.id
    assert retrieved_doc.path_id == path_id
    assert content in retrieved_content  # Original content should be in the result
    assert "---" in retrieved_content  # Should have frontmatter


@pytest.mark.asyncio
async def test_read_document_by_id_not_found(document_service):
    """Test reading a document with non-existent ID."""
    with pytest.raises(DocumentNotFoundError):
        await document_service.read_document_by_path_id("99999")


@pytest.mark.asyncio
async def test_read_document_by_id_file_error(document_service, test_doc_path):
    """Test reading a document where file is missing."""

    file_path, path_id = test_doc_path

    # Create test document without actually writing the file
    doc = await document_service.repository.create({"path_id": path_id, "file_path": path_id, "checksum": "abc123"})

    with pytest.raises(DocumentError):
        await document_service.read_document_by_path_id(path_id)


@pytest.mark.asyncio
async def test_update_document_by_id(document_service, test_doc_path):
    """Test updating a document by ID."""

    file_path, path_id = test_doc_path

    # Create initial document
    original_content = "# Original\nOriginal content."
    doc = await document_service.create_document(path_id, original_content, {"type": "test"})

    # Update it
    new_content = "# Updated\nUpdated content."
    updated_doc = await document_service.update_document_by_path_id(
        path_id, new_content, {"type": "test", "status": "updated"}
    )

    # Verify DB record
    assert updated_doc.id == doc.id
    assert updated_doc.path_id == path_id
    assert updated_doc.doc_metadata == {"type": "test", "status": "updated"}

    # Verify file content
    file_content = file_path.read_text()
    assert new_content in file_content
    assert "---" in file_content  # Should have frontmatter


@pytest.mark.asyncio
async def test_update_document_no_duplicate_frontmatter(document_service, test_doc_path):
    """Test that updating a document does not result in duplicate frontmatter."""

    file_path, path_id = test_doc_path

    # Create initial document with frontmatter
    original_content = """---
id: test_docs/test.md
created: 2025-01-01T00:00:00Z
type: test
---

# Original
Original content."""

    doc = await document_service.create_document(path_id, original_content)

    # Update the document
    new_content = "# Updated\nUpdated content."
    await document_service.update_document_by_path_id(path_id, new_content)

    # Read the file and verify frontmatter
    file_content = file_path.read_text()

    # Should only have two "---" markers (start and end of frontmatter)
    assert file_content.count("---") == 2
    
    # Split content and verify structure
    _, frontmatter, content = file_content.split("---", 2)
    
    # Verify frontmatter is valid YAML and has expected fields
    metadata = yaml.safe_load(frontmatter)
    assert metadata["id"] == path_id
    assert "created" in metadata
    assert "modified" in metadata

    # Original created timestamp should be preserved
    assert metadata["created"] is not None
    
    # Updated content should be present
    assert new_content in content
