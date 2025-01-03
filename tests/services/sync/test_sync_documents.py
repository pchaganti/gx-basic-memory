"""Test sync service."""
import asyncio
from pathlib import Path
import pytest

from basic_memory.config import ProjectConfig
from basic_memory.services import DocumentService
from basic_memory.services.sync.sync_service import SyncService
from basic_memory.models import Document


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_documents(
    sync_service: SyncService, test_config: ProjectConfig, document_service: DocumentService
):
    """Test syncing document files."""
    # Create test files
    docs_dir = test_config.documents_dir
    await create_test_file(docs_dir / "new.md", "new document")
    await create_test_file(docs_dir / "modified.md", "modified document")

    # Add existing doc to DB
    doc = Document(path_id="modified.md", file_path="modified.md", checksum="12345678")
    added = await document_service.repository.add(doc)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify results
    documents = await document_service.repository.find_all()
    assert len(documents) == 2

    paths = {d.path_id for d in documents}
    assert "new.md" in paths
    assert "modified.md" in paths


@pytest.mark.asyncio
async def test_sync_new_document_adds_frontmatter(
        test_config: ProjectConfig,
        sync_service: SyncService
):
    """Test that syncing a new document adds appropriate frontmatter."""

    # Create document without frontmatter
    doc_path = test_config.documents_dir / "test.md"
    original_content = "# Test Document\n\nThis is a test."
    doc_path.write_text(original_content)

    # Sync
    await sync_service.sync(test_config.home)

    # Read updated file
    content = doc_path.read_text()

    # Verify frontmatter was added
    assert "---" in content
    assert "id: test.md" in content
    assert "created:" in content
    assert "modified:" in content

    # Original content preserved
    assert original_content in content

    # Verify document in DB
    doc = await sync_service.document_service.repository.find_by_path_id("test.md")
    assert doc is not None
    assert doc.checksum is not None
    assert doc.created_at is not None
    assert doc.updated_at is not None


@pytest.mark.asyncio
async def test_sync_modified_document_updates_frontmatter(
        test_config: ProjectConfig,
        sync_service: SyncService
):
    """Test that modifying a document updates frontmatter properly."""

    # First create and sync a document
    doc_path = test_config.documents_dir / "test.md"
    original_content = "# Test Document\n\nOriginal content."
    doc_path.write_text(original_content)
    await sync_service.sync(test_config.home)

    # Get original timestamps
    doc = await sync_service.document_service.repository.find_by_path_id("test.md")
    original_created = doc.created_at
    original_modified = doc.updated_at

    await asyncio.sleep(1)
    
    # Modify document
    new_content = "# Test Document\n\nUpdated content."
    doc_path.write_text(new_content)
    await sync_service.sync(test_config.home)

    # Verify document in DB
    updated_doc = await sync_service.document_service.repository.find_by_path_id("test.md")
    assert updated_doc.created_at == original_created  # Should not change
    assert updated_doc.updated_at > original_modified  # Should be updated

    # Check file content
    content = doc_path.read_text()
    assert "Updated content" in content
    assert "created:" in content
    assert "modified:" in content