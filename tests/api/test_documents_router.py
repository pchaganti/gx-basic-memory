"""Tests for document management API endpoints."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from basic_memory.config import ProjectConfig
from basic_memory.schemas.search import SearchItemType, SearchResponse


@pytest.mark.asyncio
async def test_document_indexing(client: AsyncClient, test_config):
    """Test document creation includes search indexing."""
    test_doc = {
        "path_id": "test.md",
        "content": "# Test\nThis is a test document with unique searchable content.",
        "doc_metadata": {"type": "test", "tags": ["documentation", "test"]},
    }

    # Create document
    response = await client.post("/documents/create", json=test_doc)
    assert response.status_code == 201

    # Verify it's searchable
    search_response = await client.post(
        "/search/",
        json={"text": "unique searchable content", "types": [SearchItemType.DOCUMENT.value]},
    )
    assert search_response.status_code == 200
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 1
    assert search_result.results[0].path_id == "test.md"
    assert search_result.results[0].type == SearchItemType.DOCUMENT.value


@pytest.mark.asyncio
async def test_document_update_indexing(client: AsyncClient):
    """Test document updates are reflected in search index."""
    # Create initial document
    test_doc = {
        "path_id": "test.md",
        "content": "Original content without special terms.",
        "doc_metadata": {"type": "test", "status": "draft"},
    }
    create_response = await client.post("/documents/create", json=test_doc)
    assert create_response.status_code == 201

    # Update document with new content
    update_doc = {
        "path_id": "test.md",
        "content": "Updated content with special sphinx terms.",
        "doc_metadata": {"type": "test", "status": "final"},
    }
    update_response = await client.put(f"/documents/{test_doc["path_id"]}", json=update_doc)
    assert update_response.status_code == 200

    # Search for new terms
    search_response = await client.post(
        "/search/", json={"text": "sphinx", "types": [SearchItemType.DOCUMENT.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 1
    assert search_result.results[0].path_id == "test.md"

    # Original terms shouldn't be found
    search_response = await client.post(
        "/search/", json={"text": "without special", "types": [SearchItemType.DOCUMENT.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 0


@pytest.mark.asyncio
async def test_document_delete_indexing(client: AsyncClient):
    """Test deleted documents are removed from search index."""
    # Create document
    test_doc = {
        "path_id": "test.md",
        "content": "Searchable content that should disappear.",
        "doc_metadata": {"type": "test"},
    }
    create_response = await client.post("/documents/create", json=test_doc)
    assert create_response.status_code == 201

    # Verify it's initially searchable
    search_response = await client.post(
        "/search/", json={"text": "should disappear", "types": [SearchItemType.DOCUMENT.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 1

    # Delete document
    delete_response = await client.delete(f"/documents/{test_doc["path_id"]}")
    assert delete_response.status_code == 204

    # Verify it's no longer searchable
    search_response = await client.post(
        "/search/", json={"text": "should disappear", "types": [SearchItemType.DOCUMENT.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 0


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient, test_config):
    """Test document creation endpoint."""
    test_doc = {
        "path_id": "test.md",
        "content": "# Test\nThis is a test document.",
        "doc_metadata": {"type": "test", "tags": ["documentation", "test"]},
    }

    response = await client.post("/documents/create", json=test_doc)
    assert response.status_code == 201

    data = response.json()
    assert data["path_id"] == "test.md"
    assert data["doc_metadata"] == test_doc["doc_metadata"]
    assert data["checksum"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    # File should exist with both frontmatter and content
    doc_path = Path(test_config.documents_dir / "test.md")
    assert doc_path.exists()
    content = doc_path.read_text()
    assert "---" in content  # Has frontmatter
    assert "# Test" in content  # Has our content


@pytest.mark.asyncio
async def test_create_document_should_create_path(client: AsyncClient):
    """Test creating document in non-existent directory."""
    test_doc = {
        "path_id": "nonexistent/test.md",
        "content": "test content",
        "doc_metadata": {"type": "test"},
    }

    response = await client.post("/documents/create", json=test_doc)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_document_absolute_path(client: AsyncClient, tmp_path: Path):
    """Test creating document with absolute path - should fail with 400 error."""
    test_doc = {
        "path_id": str(tmp_path / "documents" / "test.md"),
        "content": "test content",
        "doc_metadata": {"type": "test"},
    }

    response = await client.post("/documents/create", json=test_doc)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient):
    """Test document retrieval endpoint."""
    test_doc = {
        "path_id": "test.md",
        "content": "# Test\nThis is a test document.",
        "doc_metadata": {"type": "test"},
    }

    # Create document
    create_response = await client.post("/documents/create", json=test_doc)
    assert create_response.status_code == 201
    created = create_response.json()

    # Get document by ID
    response = await client.get(f"/documents/{created["path_id"]}")

    assert response.status_code == 200
    data = response.json()
    assert data["path_id"] == "test.md"
    assert data["doc_metadata"] == test_doc["doc_metadata"]

    # Content checks - frontmatter followed by original content
    content = data["content"]
    assert "---" in content  # Has frontmatter
    assert "id:" in content  # Has generated ID
    assert "# Test" in content  # Has heading
    assert "This is a test document" in content  # Has body


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: AsyncClient):
    """Test getting a document that doesn't exist."""
    response = await client.get("/documents/bad_file.md")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_document(client: AsyncClient, test_config: ProjectConfig):
    """Test document update endpoint using document ID."""
    # Create initial document
    test_doc = {
        "path_id": "test.md",
        "content": "# Original\nOriginal content.",
        "doc_metadata": {"type": "test", "status": "draft"},
    }
    create_response = await client.post("/documents/create", json=test_doc)
    assert create_response.status_code == 201
    created = create_response.json()

    # Update the document
    update_doc = {
        "path_id": "test.md",
        "content": "# Updated\nUpdated content.",
        "doc_metadata": {"type": "test", "status": "final"},
    }
    response = await client.put(f"/documents/{created["path_id"]}", json=update_doc)
    assert response.status_code == 200

    data = response.json()
    assert data["doc_metadata"] == update_doc["doc_metadata"]
    assert data["path_id"] == created["path_id"]
    assert "# Updated" in data["content"]
    assert "Updated content" in data["content"]

    # Verify file was updated
    doc_path = Path(test_config.documents_dir / "test.md")
    content = doc_path.read_text()
    assert "# Updated" in content
    assert "Updated content" in content


@pytest.mark.asyncio
async def test_update_nonexistent_document(client: AsyncClient):
    """Test updating a document that doesn't exist."""
    update_doc = {
        "path_id": "bad_file.md",  # Non-existent doc path
        "content": "new content",
        "doc_metadata": {"type": "test"},
    }
    response = await client.put(f"/documents/{update_doc["path_id"]}", json=update_doc)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, test_config: ProjectConfig):
    """Test document deletion endpoint."""
    test_doc = {
        "path_id": "test.md",
        "content": "# Test\nTest content.",
        "doc_metadata": {"type": "test"},
    }

    # Create document
    create_response = await client.post("/documents/create", json=test_doc)
    assert create_response.status_code == 201
    created = create_response.json()

    # Delete document by path_id
    response = await client.delete(f"/documents/{created["path_id"]}")
    assert response.status_code == 204

    # Verify document is gone from filesystem
    doc_path = Path(test_config.documents_dir / test_doc["path_id"])
    assert not doc_path.exists()

    # Verify document is gone from DB (404 on get)
    get_response = await client.get(f"/documents/{created["path_id"]}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient):
    """Test deleting a document that doesn't exist."""
    response = await client.delete("/documents/bad_file.md")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, tmp_path: Path):
    """Test document listing endpoint."""
    # Create a few test documents
    docs = [
        {
            "path_id": "doc1.md",
            "content": "# Doc 1",
            "doc_metadata": {"type": "test", "number": 1},
        },
        {
            "path_id": "doc2.md",
            "content": "# Doc 2",
            "doc_metadata": {"type": "test", "number": 2},
        },
    ]

    # Create all documents
    created_docs = []
    for doc in docs:
        response = await client.post("/documents/create", json=doc)
        assert response.status_code == 201
        created_docs.append(response.json())

    # List all documents
    response = await client.get("/documents/list")
    assert response.status_code == 200
    data = response.json()

    # We should have both documents
    assert len(data) == 2

    # Verify all documents are present by ID
    path_ids = {item["path_id"] for item in data}
    expected_ids = {doc["path_id"] for doc in created_docs}
    assert path_ids == expected_ids

    # Verify metadata was preserved
    for item in data:
        matching_doc = next(d for d in created_docs if d["path_id"] == item["path_id"])
        assert item["doc_metadata"] == matching_doc["doc_metadata"]
