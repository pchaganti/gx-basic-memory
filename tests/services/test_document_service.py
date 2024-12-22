"""Tests for DocumentService."""

import os
import pytest
import pytest_asyncio
import yaml
from datetime import datetime
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
async def test_create_document_with_frontmatter(document_service, test_doc_path):
    """Test that created documents have proper frontmatter."""
    content = "# Test Document\n\nThis is a test."
    doc = await document_service.create_document(
        str(test_doc_path),
        content,
        {"type": "test"}
    )

    # Verify file content
    file_content = test_doc_path.read_text()
    
    # Parse frontmatter
    try:
        # Split content at the second "---" marker
        _, frontmatter, doc_content = file_content.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
    except Exception as e:
        pytest.fail(f"Failed to parse frontmatter: {e}")

    # Verify frontmatter contents
    assert metadata["id"] == doc.id
    assert metadata["type"] == "test"
    assert "created" in metadata
    assert "modified" in metadata
    
    # Verify timestamps are valid ISO format
    datetime.fromisoformat(metadata["created"])
    datetime.fromisoformat(metadata["modified"])
    
    # Verify original content is preserved
    assert content in doc_content

    # Verify DB record
    assert doc.path == str(test_doc_path)
    assert doc.doc_metadata == {"type": "test"}
    assert doc.checksum is not None


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
async def test_create_document_cleanup_on_write_failure(document_service, test_doc_path):
    """Test that failed document creation cleans up DB record when file write fails."""
    def fail_write(self, content):
        raise PermissionError("Mock write failure")
    
    # Store original write_text method
    original_write_text = Path.write_text
    
    try:
        # Replace write_text with our failing version
        Path.write_text = fail_write
        
        with pytest.raises(DocumentWriteError) as exc_info:
            await document_service.create_document(
                str(test_doc_path),
                "test content",
                {"type": "test"}
            )
        
        assert "Mock write failure" in str(exc_info.value)
        
        # Verify DB record was cleaned up
        doc = await document_service.repository.find_by_path(str(test_doc_path))
        assert doc is None
        
        # Verify no file was created
        assert not test_doc_path.exists()
        
    finally:
        # Restore original write_text method
        Path.write_text = original_write_text


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