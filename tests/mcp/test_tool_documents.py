"""Tests for document management MCP tools."""

import pytest

from basic_memory.mcp.tools.documents import (
    create_document, 
    get_document, 
    update_document,
    list_documents,
    delete_document
)
from basic_memory.schemas.request import DocumentRequest


@pytest.mark.asyncio
async def test_create_document(client):
    """Test creating a new document."""
    # Create a simple document
    request = DocumentRequest(
        path_id="test/simple.md",
        content="# Simple Test\n\nThis is a test document.",
        doc_metadata={"status": "draft"}
    )
    result = await create_document(request)

    # Verify the result
    assert result.path_id == "test/simple.md"
    assert result.doc_metadata == {"status": "draft"}
    assert result.checksum is not None
    assert result.created_at is not None
    assert result.updated_at is not None


@pytest.mark.asyncio
async def test_get_document(client):
    """Test retrieving a document."""
    # First create a document
    create_request = DocumentRequest(
        path_id="test/get_test.md",
        content="# Get Test\n\nThis is a test document.",
        doc_metadata={"version": "1.0"}
    )
    await create_document(create_request)

    # Get the document
    result = await get_document("test/get_test.md")

    # Verify the content
    assert result.path_id == "test/get_test.md"
    assert "# Get Test" in result.content
    assert result.doc_metadata == {"version": "1.0"}


@pytest.mark.asyncio
async def test_update_document(client):
    """Test updating an existing document."""
    # Create initial document
    initial_request = DocumentRequest(
        path_id="test/update_test.md",
        content="# Original Content",
        doc_metadata={"version": "1.0"}
    )
    await create_document(initial_request)

    # Update the document
    update_request = DocumentRequest(
        path_id="test/update_test.md",
        content="# Updated Content",
        doc_metadata={"version": "1.1"}
    )
    result = await update_document(update_request)

    # Verify the update
    assert result.path_id == "test/update_test.md"
    assert "# Updated Content" in result.content
    assert result.doc_metadata == {"version": "1.1"}
    assert result.created_at is not None
    assert result.updated_at is not None


@pytest.mark.asyncio
async def test_list_documents(client):
    """Test listing all documents."""
    # Create a few test documents
    docs = [
        DocumentRequest(
            path_id="test/doc1.md",
            content="# Doc 1",
            doc_metadata={"order": 1}
        ),
        DocumentRequest(
            path_id="test/doc2.md",
            content="# Doc 2",
            doc_metadata={"order": 2}
        )
    ]
    for doc in docs:
        await create_document(doc)

    # List all documents
    result = await list_documents()

    # Verify we can find our test documents
    test_docs = [doc for doc in result 
                if doc.path_id in ["test/doc1.md", "test/doc2.md"]]
    assert len(test_docs) == 2
    assert any(doc.doc_metadata.get("order") == 1 for doc in test_docs)
    assert any(doc.doc_metadata.get("order") == 2 for doc in test_docs)


@pytest.mark.asyncio
async def test_delete_document(client):
    """Test deleting a document."""
    # First create a document
    create_request = DocumentRequest(
        path_id="test/to_delete.md",
        content="# Delete Test"
    )
    await create_document(create_request)

    # Delete the document
    result = await delete_document("test/to_delete.md")
    assert result["deleted"] is True

    # Verify it's gone by trying to fetch it
    with pytest.raises(Exception):  # Document not found
        await get_document("test/to_delete.md")


@pytest.mark.asyncio
async def test_document_with_frontmatter(client):
    """Test creating and retrieving a document with frontmatter."""
    content = """---
title: Test Document
author: AI Team
version: 1.0
---

# Frontmatter Test

This document has YAML frontmatter."""

    request = DocumentRequest(
        path_id="test/frontmatter.md",
        content=content,
        doc_metadata={"has_frontmatter": True}
    )
    await create_document(request)

    # Get and verify
    result = await get_document("test/frontmatter.md")
    assert "title: Test Document" in result.content
    assert "# Frontmatter Test" in result.content


@pytest.mark.asyncio
async def test_create_document_with_nested_path(client):
    """Test creating a document in a nested directory."""
    request = DocumentRequest(
        path_id="test/nested/deep/doc.md",
        content="# Nested Test"
    )
    result = await create_document(request)
    assert result.path_id == "test/nested/deep/doc.md"

    # Verify we can retrieve it
    doc = await get_document("test/nested/deep/doc.md")
    assert "# Nested Test" in doc.content


@pytest.mark.asyncio
async def test_update_document_metadata_only(client):
    """Test updating just the metadata of a document."""
    # Create initial document
    initial_request = DocumentRequest(
        path_id="test/metadata_update.md",
        content="# Metadata Test",
        doc_metadata={"status": "draft"}
    )
    await create_document(initial_request)

    # Update only the metadata
    update_request = DocumentRequest(
        path_id="test/metadata_update.md",
        content="# Metadata Test",  # Same content
        doc_metadata={"status": "published"}  # New metadata
    )
    result = await update_document(update_request)

    assert result.content == "# Metadata Test"
    assert result.doc_metadata == {"status": "published"}