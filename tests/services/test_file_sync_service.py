"""Tests for FileSyncService."""

from pathlib import Path

import pytest
import pytest_asyncio

from basic_memory.services.file_sync_service import FileSyncService, SyncError


@pytest_asyncio.fixture
async def file_sync_service(document_repository) -> FileSyncService:
    """Create FileSyncService instance."""
    return FileSyncService(document_repository)


@pytest_asyncio.fixture
async def docs_dir(test_project_path) -> Path:
    """Get documents directory."""
    return test_project_path / "documents"


@pytest_asyncio.fixture
async def sample_files(docs_dir) -> dict[str, str]:
    """Create some sample test files."""
    # Create test structure
    design_dir = docs_dir / "design"
    notes_dir = docs_dir / "notes"
    design_dir.mkdir(exist_ok=True)
    notes_dir.mkdir(exist_ok=True)

    # Map of relative paths to content
    files = {
        "design/architecture.md": "# Architecture\nSome design notes",
        "notes/meeting.md": "# Meeting Notes\nDiscussion points",
        "README.md": "# Project\nOverview doc",
    }

    # Create files with full paths
    for rel_path, content in files.items():
        full_path = docs_dir / rel_path
        full_path.write_text(content)

    return files


@pytest.mark.asyncio
async def test_scan_files(file_sync_service, docs_dir, sample_files):
    """Test scanning directory for files."""
    scanned = await file_sync_service.scan_files(docs_dir)
    
    # Should find all files
    assert len(scanned) == len(sample_files)
    
    # Paths should be relative and match sample files
    assert set(scanned.keys()) == set(sample_files.keys())
    
    # All files should have checksums
    assert all(isinstance(checksum, str) for checksum in scanned.values())


@pytest.mark.asyncio
async def test_find_new_files(file_sync_service, docs_dir, sample_files):
    """Test detecting new files."""
    changes = await file_sync_service.find_changes(
        await file_sync_service.scan_files(docs_dir)
    )
    
    # All files should be new
    assert len(changes.new) == len(sample_files)
    assert len(changes.modified) == 0
    assert len(changes.deleted) == 0


@pytest.mark.asyncio
async def test_find_modified_files(file_sync_service, docs_dir, sample_files):
    """Test detecting modified files."""
    # First sync to create DB records
    await file_sync_service.sync(docs_dir)
    
    # Modify a file
    mod_path = docs_dir / "design/architecture.md"
    mod_path.write_text("# Updated Architecture")
    
    # Check changes
    changes = await file_sync_service.find_changes(
        await file_sync_service.scan_files(docs_dir)
    )
    
    assert len(changes.modified) == 1
    assert "design/architecture.md" in changes.modified
    assert len(changes.new) == 0
    assert len(changes.deleted) == 0


@pytest.mark.asyncio
async def test_find_deleted_files(file_sync_service, docs_dir, sample_files):
    """Test detecting deleted files."""
    # First sync to create DB records
    await file_sync_service.sync(docs_dir)
    
    # Delete a file
    del_path = docs_dir / "notes/meeting.md"
    del_path.unlink()
    
    # Check changes
    changes = await file_sync_service.find_changes(
        await file_sync_service.scan_files(docs_dir)
    )
    
    assert len(changes.deleted) == 1
    assert "notes/meeting.md" in changes.deleted
    assert len(changes.new) == 0
    assert len(changes.modified) == 0


@pytest.mark.asyncio
async def test_full_sync_process(file_sync_service, docs_dir, sample_files):
    """Test full sync process with various changes."""
    # First sync to create initial state
    initial_sync = await file_sync_service.sync(docs_dir)
    assert initial_sync.total_changes == len(sample_files)
    
    # Make some changes:
    # 1. Add new file
    (docs_dir / "notes").mkdir(exist_ok=True)  # Ensure parent exists
    (docs_dir / "notes/todo.md").write_text("# TODO\n- First item")
    
    # 2. Modify existing file
    (docs_dir / "README.md").write_text("# Updated Project")
    
    # 3. Delete a file
    (docs_dir / "design/architecture.md").unlink()
    
    # Run sync
    changes = await file_sync_service.sync(docs_dir)
    
    # Verify changes
    assert len(changes.new) == 1
    assert "notes/todo.md" in changes.new
    
    assert len(changes.modified) == 1
    assert "README.md" in changes.modified
    
    assert len(changes.deleted) == 1
    assert "design/architecture.md" in changes.deleted


@pytest.mark.asyncio
async def test_no_changes_sync(file_sync_service, docs_dir, sample_files):
    """Test sync when no changes are present."""
    # First sync to create initial state
    await file_sync_service.sync(docs_dir)
    
    # Sync again immediately
    changes = await file_sync_service.sync(docs_dir)
    
    # Should detect no changes
    assert changes.total_changes == 0


@pytest.mark.asyncio
async def test_sync_empty_directory(file_sync_service, docs_dir):
    """Test syncing an empty directory."""
    changes = await file_sync_service.sync(docs_dir)
    assert changes.total_changes == 0


@pytest.mark.asyncio
async def test_error_on_unreadable_file(file_sync_service, docs_dir):
    """Test handling of unreadable files during sync."""
    # Create file without read permissions
    bad_file = docs_dir / "bad.md"
    bad_file.write_text("test")
    bad_file.chmod(0o000)  # Remove all permissions
    
    with pytest.raises(SyncError):
        await file_sync_service.sync(docs_dir)
    
    # Clean up
    bad_file.chmod(0o666)  # Make readable/writable for cleanup