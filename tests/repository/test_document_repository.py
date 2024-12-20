"""Tests for the DocumentRepository."""

import json
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
            path="test/sample.md",
            checksum="abc123",
            doc_metadata={"type": "test", "tags": ["sample"]}
        )
        session.add(doc)
        return doc


@pytest.mark.asyncio
async def test_create_document(document_repository: DocumentRepository):
    """Test creating a new document."""
    doc_data = {
        "path": "test/doc1.md",
        "checksum": "xyz789",
        "doc_metadata": {
            "type": "note",
            "tags": ["test"]
        }
    }
    doc = await document_repository.create(doc_data)

    # Verify returned object
    assert doc.path == "test/doc1.md"
    assert doc.checksum == "xyz789"
    assert doc.doc_metadata == {"type": "note", "tags": ["test"]}
    assert isinstance(doc.created_at, datetime)

    # Verify in database
    async with db.scoped_session(document_repository.session_maker) as session:
        stmt = select(Document).where(Document.id == doc.id)
        result = await session.execute(stmt)
        db_doc = result.scalar_one()
        assert db_doc.path == doc.path
        assert db_doc.checksum == doc.checksum
        assert db_doc.doc_metadata == doc.doc_metadata


@pytest.mark.asyncio
async def test_find_by_path(document_repository: DocumentRepository, sample_doc):
    """Test finding a document by path."""
    found = await document_repository.find_by_path(sample_doc.path)
    assert found is not None
    assert found.id == sample_doc.id
    assert found.path == sample_doc.path
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
        sample_doc.path: "different_checksum",  # Changed
        "new/doc.md": "new123"  # New file
    }

    changed = await document_repository.find_changed(checksums)
    assert len(changed) == 1
    assert changed[0].path == sample_doc.path


@pytest.mark.asyncio
async def test_update_document(document_repository: DocumentRepository, sample_doc):
    """Test updating a document."""
    new_metadata = {"type": "updated", "tags": ["modified"]}
    updated = await document_repository.update(
        sample_doc.id,
        {"checksum": "new456", "doc_metadata": new_metadata}
    )

    assert updated is not None
    assert updated.checksum == "new456"
    assert updated.doc_metadata == new_metadata
    assert updated.path == sample_doc.path  # Path unchanged

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
    found = await document_repository.find_by_path(sample_doc.path)
    assert found is None


@pytest.mark.asyncio
async def test_unique_path_constraint(document_repository: DocumentRepository, sample_doc):
    """Test that document paths must be unique."""
    # Try to create a document with same path
    doc_data = {
        "path": sample_doc.path,  # Same path
        "checksum": "different",
        "doc_metadata": {"type": "duplicate"}
    }

    with pytest.raises(Exception) as exc_info:
        await document_repository.create(doc_data)
    assert "UNIQUE constraint" in str(exc_info.value)