"""Tests for document management API endpoints."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from basic_memory.schemas.response import DocumentCreateResponse


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
