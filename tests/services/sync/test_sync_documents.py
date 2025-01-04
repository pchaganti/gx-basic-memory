"""Test document sync functionality."""
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
    sync_service: SyncService, 
    test_config: ProjectConfig, 
    document_service: DocumentService
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
    await sync_service.sync(test_config)

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
    await sync_service.sync(test_config)

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
    await sync_service.sync(test_config)

    # Get original timestamps
    doc = await sync_service.document_service.repository.find_by_path_id("test.md")
    original_created = doc.created_at
    original_modified = doc.updated_at

    await asyncio.sleep(1)  # Ensure timestamps will be different
    
    # Modify document
    new_content = "# Test Document\n\nUpdated content."
    doc_path.write_text(new_content)
    await sync_service.sync(test_config)

    # Verify document in DB
    updated_doc = await sync_service.document_service.repository.find_by_path_id("test.md")
    assert updated_doc.created_at == original_created  # Should not change
    assert updated_doc.updated_at > original_modified  # Should be updated

    # Check file content
    content = doc_path.read_text()
    assert "Updated content" in content
    assert "created:" in content
    assert "modified:" in content


@pytest.mark.asyncio
async def test_sync_document_with_invalid_frontmatter(
    test_config: ProjectConfig,
    sync_service: SyncService
):
    """Test syncing a document with malformed frontmatter."""
    # Create document with invalid frontmatter
    doc_path = test_config.documents_dir / "invalid.md"
    content = """---
id: this should be: invalid
created: not-a-date
modified: also-not-a-date
---

# Test Document
Content here.
"""
    doc_path.write_text(content)

    # Sync should fix the frontmatter
    await sync_service.sync(test_config)

    # Read updated file
    updated_content = doc_path.read_text()

    # Verify frontmatter was fixed
    assert "---" in updated_content
    assert "id: invalid.md" in updated_content  # Should use filename
    # Should have valid dates
    assert "T" in updated_content  # ISO format contains 'T'
    assert "T" in updated_content  # ISO format contains 'T'

    # Original content preserved
    assert "# Test Document" in updated_content
    assert "Content here." in updated_content

    # Verify document in DB
    doc = await sync_service.document_service.repository.find_by_path_id("invalid.md")
    assert doc is not None
    assert doc.checksum is not None


@pytest.mark.asyncio
async def test_sync_document_preserve_existing_metadata(
    test_config: ProjectConfig,
    sync_service: SyncService
):
    """Test that sync preserves custom metadata fields in frontmatter."""
    # Create document with custom metadata
    doc_path = test_config.documents_dir / "metadata.md"
    content = """---
id: metadata.md
created: 2024-01-01T00:00:00Z
modified: 2024-01-01T00:00:00Z
custom_field: custom value
tags:
  - tag1
  - tag2
author: Test Author
---

# Document with Metadata
"""
    doc_path.write_text(content)

    # Sync
    await sync_service.sync(test_config)

    # Read updated file
    updated_content = doc_path.read_text()

    # Verify custom fields preserved
    assert "custom_field: custom value" in updated_content
    assert "tags:" in updated_content
    assert "- tag1" in updated_content
    assert "- tag2" in updated_content
    assert "author: Test Author" in updated_content

    # Required fields still present
    assert "id: metadata.md" in updated_content
    assert "created:" in updated_content
    assert "modified:" in updated_content


@pytest.mark.asyncio
async def test_sync_document_in_subdirectory(
    test_config: ProjectConfig,
    sync_service: SyncService
):
    """Test syncing documents in nested directory structure."""
    # Create nested directories and files
    base_dir = test_config.documents_dir
    nested_path = base_dir / "folder1" / "folder2" / "nested.md"
    nested_path.parent.mkdir(parents=True)
    
    content = "# Nested Document\nIn subfolder"
    nested_path.write_text(content)

    # Sync
    await sync_service.sync(test_config)

    # Verify document in DB with correct path
    expected_path = "folder1/folder2/nested.md"
    doc = await sync_service.document_service.repository.find_by_path_id(expected_path)
    assert doc is not None
    assert doc.file_path == expected_path

    # Verify frontmatter has correct path
    content = nested_path.read_text()
    assert f"id: {expected_path}" in content


@pytest.mark.asyncio
async def test_sync_empty_document(
    test_config: ProjectConfig,
    sync_service: SyncService
):
    """Test syncing an empty document."""
    # Create empty file
    doc_path = test_config.documents_dir / "empty.md"
    doc_path.write_text("")

    # Sync
    await sync_service.sync(test_config)

    # Should still add frontmatter
    content = doc_path.read_text()
    assert "---" in content
    assert "id: empty.md" in content
    assert "created:" in content
    assert "modified:" in content

    # Verify in DB
    doc = await sync_service.document_service.repository.find_by_path_id("empty.md")
    assert doc is not None
    assert doc.checksum is not None


@pytest.mark.asyncio
async def test_sync_document_utf8_encoding(
    test_config: ProjectConfig,
    sync_service: SyncService
):
    """Test syncing documents with non-ASCII characters."""
    # Create document with UTF-8 content
    doc_path = test_config.documents_dir / "utf8.md"
    content = """# UTF-8 Test 🚀
    
## Special Characters
- Chinese: 你好世界
- Japanese: こんにちは
- Emoji: 🌟 ⭐️ 🌍
- Accents: éèêë ñ ü

## Various Symbols
§ ¢ € ¥ © ®️ ™️
"""
    doc_path.write_text(content, encoding='utf-8')

    # Sync
    await sync_service.sync(test_config)

    # Read back and verify content preserved
    updated_content = doc_path.read_text(encoding='utf-8')
    assert "你好世界" in updated_content
    assert "こんにちは" in updated_content
    assert "🚀" in updated_content
    assert "éèêë" in updated_content

    # Verify document in DB
    doc = await sync_service.document_service.repository.find_by_path_id("utf8.md")
    assert doc is not None
    assert doc.checksum is not None