"""Tests for document management API endpoints."""

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient, tmp_path: Path):
    """Test document creation endpoint."""
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Test\nThis is a test document.",
        "doc_metadata": {"type": "test", "tags": ["documentation", "test"]},
    }

    response = await client.post("/documents/", json=test_doc)
    data = response.json()

    assert response.status_code == 201
    assert data["path"] == test_doc["path"]
    assert data["doc_metadata"] == test_doc["doc_metadata"]
    assert data["checksum"] is not None
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    # Verify file was created with content
    doc_path = Path(test_doc["path"])
    assert doc_path.exists()
    content = doc_path.read_text()
    assert "# Test" in content
    assert "---" in content  # Has frontmatter


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, tmp_path: Path):
    """Test document retrieval endpoint."""
    # First create a document
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Test\nThis is a test document.",
        "doc_metadata": {"type": "test"},
    }

    # Create document
    create_response = await client.post("/documents/", json=test_doc)
    assert create_response.status_code == 201

    # Get document
    response = await client.get(f"/documents/{test_doc['path']}")

    assert response.status_code == 200
    data = response.json()
    assert data["path"] == test_doc["path"]
    assert data["content"] == test_doc["content"]
    assert data["doc_metadata"] == test_doc["doc_metadata"]


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: AsyncClient, tmp_path: Path):
    """Test error handling for non-existent document."""
    response = await client.get(f"/documents/{tmp_path}/nonexistent.md")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_document(client: AsyncClient, tmp_path: Path):
    """Test document update endpoint."""
    # First create a document
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Test\nOriginal content",
        "doc_metadata": {"type": "test", "status": "draft"},
    }

    # Create document
    create_response = await client.post("/documents/", json=test_doc)
    assert create_response.status_code == 201
    created = create_response.json()

    # Update document
    update_doc = {
        "id": created["id"],
        "checksum": created["checksum"],
        "content": "# Test\nUpdated content",
        "doc_metadata": {"type": "test", "status": "final"},
    }
    response = await client.put(f"/documents/{test_doc['path']}", json=update_doc)

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == update_doc["content"]
    assert data["doc_metadata"] == update_doc["doc_metadata"]
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, tmp_path: Path):
    """Test document deletion endpoint."""
    # First create a document
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Test\nThis is a test document.",
        "doc_metadata": {"type": "test"},
    }

    # Create document
    create_response = await client.post("/documents/", json=test_doc)
    assert create_response.status_code == 201

    # Delete document
    response = await client.delete(f"/documents/{test_doc['path']}")

    assert response.status_code == 204

    # Verify file is gone
    assert not Path(test_doc["path"]).exists()


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, tmp_path: Path):
    """Test document listing endpoint."""
    # Create a couple of documents
    docs = [
        {
            "path": str(tmp_path / "test1.md"),
            "content": "# Test 1",
            "doc_metadata": {"type": "test"},
        },
        {
            "path": str(tmp_path / "test2.md"),
            "content": "# Test 2",
            "doc_metadata": {"type": "test"},
        },
    ]

    # Create documents
    for doc in docs:
        response = await client.post("/documents/", json=doc)
        assert response.status_code == 201

    # List documents
    response = await client.get("/documents/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {d["path"] for d in data} == {d["path"] for d in docs}
