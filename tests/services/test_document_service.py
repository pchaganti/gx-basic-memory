"""Tests for DocumentService."""

import os
import pytest
import pytest_asyncio
from pathlib import Path
import stat

from basic_memory.services.document_service import (
    DocumentService,
    DocumentNotFoundError,
    DocumentWriteError
)


@pytest_asyncio.fixture
async def document_service(document_repository) -> DocumentService:
    """Create DocumentService instance."""
    return DocumentService(document_repository)


@pytest_asyncio.fixture
async def test_doc_path(tmp_path) -> Path:
    """Create a test document directory."""
    doc_dir = tmp_path / "test_docs"
    doc_dir.mkdir()
    return doc_dir / "test.md"


@pytest.mark.asyncio
async def test_create_document_file_first(document_service, test_doc_path):
    """Test that files are written before database records."""
    content = "# Test Document\n\nThis is a test."
    doc = await document_service.create_document(
        str(test_doc_path),
        content,
        {"type": "test"}
    )

    # Verify both file and database record
    assert test_doc_path.exists()
    assert test_doc_path.read_text() == content
    assert doc.path == str(test_doc_path)
    assert doc.doc_metadata == {"type": "test"}


@pytest.mark.asyncio
async def test_create_document_unwriteable_directory(document_service, tmp_path):
    """Test error when trying to write to an unwriteable directory."""
    # Create parent directory without write permissions
    parent_dir = tmp_path / "unwriteable"
    parent_dir.mkdir()
    parent_dir.chmod(stat.S_IREAD)  # Read-only
    
    bad_path = parent_dir / "test.md"
    content = "# Test"
    
    with pytest.raises(DocumentWriteError):
        await document_service.create_document(str(bad_path), content)
    
    # Verify directory is still read-only
    assert not os.access(parent_dir, os.W_OK)
    # Verify no database record
    doc = await document_service.repository.find_by_path(str(bad_path))
    assert doc is None
    
    # Clean up - make writable again so it can be deleted
    parent_dir.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)


@pytest.mark.asyncio
async def test_delete_nonexistent_file(document_service, test_doc_path):
    """Test deleting a file that doesn't exist."""
    with pytest.raises(DocumentNotFoundError):
        await document_service.delete_document(str(test_doc_path))


@pytest.mark.asyncio
async def test_update_nonexistent_file(document_service, test_doc_path):
    """Test updating a file that doesn't exist."""
    with pytest.raises(DocumentNotFoundError):
        await document_service.update_document(
            str(test_doc_path),
            "new content"
        )


@pytest.mark.asyncio
async def test_read_file_exists_no_record(document_service, test_doc_path):
    """Test reading a file that exists but has no database record."""
    content = "# Test\nNo record yet"
    test_doc_path.write_text(content)

    # Reading should create the record
    doc, read_content = await document_service.read_document(str(test_doc_path))
    
    assert read_content == content
    assert doc is not None
    assert doc.path == str(test_doc_path)


@pytest.mark.asyncio
async def test_read_no_file(document_service, test_doc_path):
    """Test reading a non-existent file."""
    with pytest.raises(DocumentNotFoundError):
        await document_service.read_document(str(test_doc_path))


@pytest.mark.asyncio
async def test_update_file_exists_no_record(document_service, test_doc_path):
    """Test updating a file that exists but has no database record."""
    # Create file without record
    test_doc_path.write_text("original content")

    # Update should create record
    new_content = "updated content"
    doc = await document_service.update_document(
        str(test_doc_path),
        new_content,
        {"status": "updated"}
    )

    assert doc is not None
    assert doc.path == str(test_doc_path)
    assert doc.doc_metadata == {"status": "updated"}
    assert test_doc_path.read_text() == new_content