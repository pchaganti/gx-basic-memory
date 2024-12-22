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
    assert response.status_code == 201

    data = response.json()
    assert data["path"] == test_doc["path"]
    assert data["doc_metadata"] == test_doc["doc_metadata"]
    assert data["id"] is not None
    assert data["checksum"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    # File should exist with both frontmatter and content
    doc_path = Path(test_doc["path"])
    assert doc_path.exists()
    content = doc_path.read_text()
    assert "---" in content  # Has frontmatter
    assert "# Test" in content  # Has our content


@pytest.mark.asyncio
async def test_create_document_invalid_path(client: AsyncClient, tmp_path: Path):
    """Test creating document in non-existent directory."""
    test_doc = {
        "path": str(tmp_path / "nonexistent" / "test.md"),
        "content": "test content",
        "doc_metadata": {"type": "test"},
    }

    response = await client.post("/documents/", json=test_doc)
    assert response.status_code == 201  # We now create parent directories


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, tmp_path: Path):
    """Test document retrieval endpoint."""
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Test\nThis is a test document.",
        "doc_metadata": {"type": "test"},
    }

    # Create document
    create_response = await client.post("/documents/", json=test_doc)
    assert create_response.status_code == 201
    created = create_response.json()

    # Get document
    response = await client.get(f"/documents/{test_doc['path']}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == test_doc["path"]
    assert data["doc_metadata"] == test_doc["doc_metadata"]
    
    # Content checks - frontmatter followed by original content
    content = data["content"]
    assert "---" in content  # Has frontmatter
    assert "id:" in content  # Has generated ID
    assert "# Test" in content  # Has heading
    assert "This is a test document" in content  # Has body


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: AsyncClient, tmp_path: Path):
    """Test getting a document that doesn't exist."""
    response = await client.get(f"/documents/{tmp_path}/nonexistent.md")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_document(client: AsyncClient, tmp_path: Path):
    """Test document update endpoint using document ID."""
    # Create initial document
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Original\nOriginal content.",
        "doc_metadata": {"type": "test", "status": "draft"},
    }
    create_response = await client.post("/documents/", json=test_doc)
    assert create_response.status_code == 201
    created = create_response.json()

    # Update the document
    update_doc = {
        "id": created["id"],
        "content": "# Updated\nUpdated content.",
        "doc_metadata": {"type": "test", "status": "final"},
    }
    response = await client.put(f"/documents/{created['id']}", json=update_doc)
    assert response.status_code == 200

    data = response.json()
    assert data["doc_metadata"] == update_doc["doc_metadata"]
    assert "# Updated" in data["content"]
    assert "Updated content" in data["content"]
    
    # Verify file was updated
    doc_path = Path(test_doc["path"])
    content = doc_path.read_text()
    assert "# Updated" in content
    assert "Updated content" in content


@pytest.mark.asyncio
async def test_update_nonexistent_document(client: AsyncClient):
    """Test updating a document that doesn't exist."""
    update_doc = {
        "id": 99999,  # Non-existent ID
        "content": "new content",
        "doc_metadata": {"type": "test"},
    }
    response = await client.put("/documents/99999", json=update_doc)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, tmp_path: Path):
    """Test document deletion endpoint."""
    test_doc = {
        "path": str(tmp_path / "test.md"),
        "content": "# Test\nTest content.",
        "doc_metadata": {"type": "test"},
    }

    # Create document
    create_response = await client.post("/documents/", json=test_doc)
    assert create_response.status_code == 201

    # Delete document
    response = await client.delete(f"/documents/{test_doc['path']}")
    assert response.status_code == 204

    # Verify document is gone
    doc_path = Path(test_doc["path"])
    assert not doc_path.exists()

    # Verify 404 on subsequent get
    get_response = await client.get(f"/documents/{test_doc['path']}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, tmp_path: Path):
    """Test document listing endpoint."""
    # Create a few test documents
    docs = [
        {
            "path": str(tmp_path / "doc1.md"),
            "content": "# Doc 1",
            "doc_metadata": {"type": "test", "number": 1},
        },
        {
            "path": str(tmp_path / "doc2.md"),
            "content": "# Doc 2",
            "doc_metadata": {"type": "test", "number": 2},
        },
    ]

    # Create all documents
    created_docs = []
    for doc in docs:
        response = await client.post("/documents/", json=doc)
        assert response.status_code == 201
        created_docs.append(response.json())

    # List all documents
    response = await client.get("/documents/")
    assert response.status_code == 200
    data = response.json()
    
    # We should have both documents
    assert len(data) == 2
    
    # Verify all paths are present
    paths = {item["path"] for item in data}
    expected_paths = {doc["path"] for doc in docs}
    assert paths == expected_paths

    # Verify metadata was preserved
    for item in data:
        matching_doc = next(d for d in docs if d["path"] == item["path"])
        assert item["doc_metadata"] == matching_doc["doc_metadata"]