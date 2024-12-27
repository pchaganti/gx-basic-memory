"""Test document sync service."""

import pytest
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory.models import Document
from basic_memory.services import DocumentSyncService, DocumentService, FileChangeScanner
from basic_memory.utils.file_utils import compute_checksum


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def document_sync_service(
    file_change_scanner: FileChangeScanner,  # from conftest
    document_service: DocumentService  # from conftest
) -> DocumentSyncService:
    """Create document sync service with test dependencies."""
    return DocumentSyncService(file_change_scanner, document_service)


@pytest.mark.asyncio
async def test_sync_new_files(
    document_sync_service: DocumentSyncService,
    test_config,
):
    """Test syncing new files from filesystem."""
    # Create test files
    docs_dir = test_config.documents_dir
    await create_test_file(docs_dir / "test.md", "test content")
    await create_test_file(docs_dir / "subdir/nested.md", "nested content")

    # Run sync
    changes = await document_sync_service.sync(docs_dir)

    # Verify changes reported
    assert len(changes.new) == 2
    assert "test.md" in changes.new
    assert "subdir/nested.md" in changes.new

    # Verify files in DB
    doc = await document_sync_service.document_service.read_document_by_path_id("test.md")
    assert doc[0].path_id == "test.md"
    assert doc[0].file_path == "test.md"
    assert "test content" in doc[1] 

    nested = await document_sync_service.document_service.read_document_by_path_id("subdir/nested.md")
    assert nested[0].path_id == "subdir/nested.md"
    assert nested[0].file_path == "subdir/nested.md"
    assert "nested content" in nested[1]


@pytest.mark.asyncio
async def test_sync_modified_files(
    document_sync_service: DocumentSyncService,
    test_config,
    document_repository
):
    """Test syncing modified files."""
    docs_dir = test_config.documents_dir
    path = "test.md"
    
    # Create original file and DB record
    original_content = "original content"
    await create_test_file(docs_dir / path, original_content)
    original_checksum = await compute_checksum(original_content)
    
    await document_repository.create({
        "path_id": path,
        "file_path": path,
        "checksum": original_checksum
    })

    # Modify file
    new_content = "modified content"
    await create_test_file(docs_dir / path, new_content)

    # Run sync
    changes = await document_sync_service.sync(docs_dir)

    # Verify changes reported
    assert len(changes.modified) == 1
    assert path in changes.modified

    # Verify file updated in DB
    doc = await document_sync_service.document_service.read_document_by_path_id(path)
    assert new_content in doc[1]


@pytest.mark.asyncio
async def test_sync_moved_files(
    document_sync_service: DocumentSyncService,
    test_config,
    document_repository
):
    """Test syncing moved/renamed files."""
    docs_dir = test_config.documents_dir
    original_path = "test.md"
    new_path = "new/location.md"
    content = "test content"

    # Create original file and DB record
    await create_test_file(docs_dir / original_path, content)
    checksum = await compute_checksum(content)
    
    await document_repository.create({
        "path_id": original_path,
        "file_path": original_path,
        "checksum": checksum
    })

    # Move file
    (docs_dir / original_path).unlink()
    await create_test_file(docs_dir / new_path, content)

    # Run sync
    changes = await document_sync_service.sync(docs_dir)

    # Verify changes reported
    assert len(changes.moved) == 1
    assert new_path in changes.moved
    assert changes.moved[new_path].moved_from == original_path

    # Verify file moved in DB
    with pytest.raises(Exception):
        # Original should be gone
        await document_sync_service.document_service.read_document_by_path_id(original_path)
    
    # New location should exist
    doc = await document_sync_service.document_service.read_document_by_path_id(new_path)
    assert doc[0].path_id == new_path
    assert doc[0].file_path == new_path
    assert content in doc[1]


@pytest.mark.asyncio
async def test_sync_deleted_files(
    document_sync_service: DocumentSyncService,
    test_config,
    document_repository
):
    """Test syncing deleted files."""
    docs_dir = test_config.documents_dir
    path = "to_delete.md"

    # Create DB record for non-existent file
    await document_repository.create({
        "path_id": path,
        "file_path": path,
        "checksum": "any-checksum"
    })

    # Run sync
    changes = await document_sync_service.sync(docs_dir)

    # Verify changes reported
    assert len(changes.deleted) == 1
    assert path in changes.deleted

    # Verify file deleted from DB
    with pytest.raises(Exception):
        await document_sync_service.document_service.read_document_by_path_id(path)


@pytest.mark.asyncio
async def test_sync_mixed_changes(
    document_sync_service: DocumentSyncService,
    test_config,
    document_repository
):
    """Test syncing multiple types of changes at once."""
    docs_dir = test_config.documents_dir

    # Setup initial state
    # 1. Create a file that will be modified
    mod_path = "to_modify.md"
    await create_test_file(docs_dir / mod_path, "original")
    await document_repository.create({
        "path_id": mod_path,
        "file_path": mod_path,
        "checksum": await compute_checksum("original")
    })

    # 2. Create record for a file that will be deleted
    del_path = "to_delete.md"
    await document_repository.create({
        "path_id": del_path,
        "file_path": del_path,
        "checksum": "any-checksum"
    })

    # 3. Create a file that will be moved
    move_from = "old_location.md"
    move_to = "new/location.md"
    content = "to be moved"
    await create_test_file(docs_dir / move_from, content)
    await document_repository.create({
        "path_id": move_from,
        "file_path": move_from,
        "checksum": await compute_checksum(content)
    })

    # Make changes
    # 1. Modify file
    await create_test_file(docs_dir / mod_path, "modified")
    
    # 2. Move file
    (docs_dir / move_from).unlink()
    await create_test_file(docs_dir / move_to, content)

    # 3. Create new file
    await create_test_file(docs_dir / "new_file.md", "new content")

    # Run sync
    changes = await document_sync_service.sync(docs_dir)

    # Verify all changes
    assert len(changes.new) == 1
    assert "new_file.md" in changes.new

    assert len(changes.modified) == 1
    assert mod_path in changes.modified

    assert len(changes.deleted) == 1
    assert del_path in changes.deleted

    assert len(changes.moved) == 1
    assert move_to in changes.moved
    assert changes.moved[move_to].moved_from == move_from