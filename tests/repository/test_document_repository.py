"""Tests for the DocumentRepository."""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from basic_memory import db
from basic_memory.models import Document
from basic_memory.repository.document_repository import DocumentRepository


@pytest_asyncio.fixture
async def sample_doc(session_maker):
    """Create a sample document."""
    async with db.scoped_session(session_maker) as session:
        doc = Document(
            path_id="test/sample.md",
            file_path="test/Sample.md",
            checksum="abc123",
            doc_metadata={"type": "test", "tags": ["sample"]},
        )
        session.add(doc)
        return doc


@pytest.mark.asyncio
async def test_basic_document_operations(document_repository: DocumentRepository):
    """Smoke test for basic document operations."""
    # Create
    doc_data = {
        "path_id": "test/basic.md",
        "file_path": "test/Basic.md",
        "checksum": "test123",
        "doc_metadata": {"type": "test"},
    }
    doc = await document_repository.create(doc_data)

    # Read
    found = await document_repository.find_by_path_id("test/basic.md")
    assert found is not None
    assert found.checksum == "test123"

    # Update
    updated = await document_repository.update(doc.id, {"checksum": "changed123"})
    assert updated.checksum == "changed123"

    # Delete
    result = await document_repository.delete(doc.id)
    assert result is True

    # Verify deletion
    not_found = await document_repository.find_by_path_id("test/basic.md")
    assert not_found is None


@pytest.mark.asyncio
async def test_create_document(document_repository: DocumentRepository):
    """Test creating a new document."""
    doc_data = {
        "path_id": "test/doc1.md",
        "file_path": "test/Doc1.md",
        "checksum": "xyz789",
        "doc_metadata": {"type": "note", "tags": ["test"]},
    }
    doc = await document_repository.create(doc_data)

    # Verify returned object
    assert doc.path_id == "test/doc1.md"
    assert doc.checksum == "xyz789"
    assert doc.doc_metadata == {"type": "note", "tags": ["test"]}
    assert isinstance(doc.created_at, datetime)

    # Verify in database
    async with db.scoped_session(document_repository.session_maker) as session:
        stmt = select(Document).where(Document.id == doc.id)
        result = await session.execute(stmt)
        db_doc = result.scalar_one()
        assert db_doc.path_id == doc.path_id
        assert db_doc.file_path == doc.file_path
        assert db_doc.checksum == doc.checksum
        assert db_doc.doc_metadata == doc.doc_metadata


@pytest.mark.asyncio
async def test_find_by_path(document_repository: DocumentRepository, sample_doc):
    """Test finding a document by path."""
    found = await document_repository.find_by_path_id(sample_doc.path_id)
    assert found is not None
    assert found.id == sample_doc.id
    assert found.path_id == sample_doc.path_id
    assert found.checksum == sample_doc.checksum


@pytest.mark.asyncio
async def test_find_by_checksum(document_repository: DocumentRepository, sample_doc):
    """Test finding documents by checksum."""
    found = await document_repository.find_by_checksum(sample_doc.checksum)
    assert len(found) == 1
    assert found[0].id == sample_doc.id
    assert found[0].checksum == sample_doc.checksum


@pytest.mark.asyncio
async def test_find_changed_documents(document_repository: DocumentRepository, sample_doc):
    """Test finding changed documents based on checksums."""
    checksums = {
        sample_doc.path_id: "different_checksum",  # Changed
        "new/doc.md": "new123",  # New file
    }

    changed = await document_repository.find_changed(checksums)
    assert len(changed) == 1
    assert changed[0].path_id == sample_doc.path_id


@pytest.mark.asyncio
async def test_update_document(document_repository: DocumentRepository, sample_doc):
    """Test updating a document."""
    new_metadata = {"type": "updated", "tags": ["modified"]}
    updated = await document_repository.update(
        sample_doc.id, {"checksum": "new456", "doc_metadata": new_metadata}
    )

    assert updated is not None
    assert updated.checksum == "new456"
    assert updated.doc_metadata == new_metadata
    assert updated.path_id == sample_doc.path_id  # Path unchanged

    # Verify in database
    async with db.scoped_session(document_repository.session_maker) as session:
        stmt = select(Document).where(Document.id == sample_doc.id)
        result = await session.execute(stmt)
        db_doc = result.scalar_one()
        assert db_doc.checksum == "new456"
        assert db_doc.doc_metadata == new_metadata


@pytest.mark.asyncio
async def test_delete_document(document_repository: DocumentRepository, sample_doc):
    """Test deleting a document."""
    result = await document_repository.delete(sample_doc.id)
    assert result is True

    # Verify deletion
    found = await document_repository.find_by_path_id(sample_doc.path_id)
    assert found is None


@pytest.mark.asyncio
async def test_unique_path_constraint(document_repository: DocumentRepository, sample_doc):
    """Test that document paths must be unique."""
    # Try to create a document with same path
    doc_data = {
        "path_id": sample_doc.path_id,  # Same path
        "file_path": "test/Basic.md",
        "checksum": "different",
        "doc_metadata": {"type": "duplicate"},
    }

    with pytest.raises(Exception) as exc_info:
        await document_repository.create(doc_data)
    assert "UNIQUE constraint" in str(exc_info.value)
