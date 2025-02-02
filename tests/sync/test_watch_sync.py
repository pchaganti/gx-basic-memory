"""Tests for watch service integration with sync service."""

import pytest
import pytest_asyncio
from pathlib import Path
from watchfiles import Change

from basic_memory.sync.utils import FileChange


@pytest.mark.asyncio
async def test_sync_with_file_changes(sync_service, tmp_path):
    """Test sync with file changes from watch service"""
    # Create a test file
    content = """---
title: Test Note
type: note
---
# Test Note
This is a test."""
    
    file_path = tmp_path / "test.md"
    file_path.write_text(content)
    
    # Create FileChange for a new file
    changes = {
        str(file_path): FileChange(
            change_type=Change.added,
            path=str(file_path),
            checksum="abc123"
        )
    }
    
    report = await sync_service.sync(file_changes=changes)
    assert str(file_path) in report.new
    assert report.checksums[str(file_path)] == "abc123"


@pytest.mark.asyncio
async def test_sync_mixed_changes(sync_service, tmp_path):
    """Test sync with multiple types of changes"""
    # Setup initial files
    new_file = tmp_path / "new.md"
    new_file.write_text("New file")
    
    mod_file = tmp_path / "modified.md"
    mod_file.write_text("Original content")
    
    del_file = tmp_path / "deleted.md"
    
    changes = {
        str(new_file): FileChange(
            change_type=Change.added,
            path=str(new_file),
            checksum="new123"
        ),
        str(mod_file): FileChange(
            change_type=Change.modified,
            path=str(mod_file),
            checksum="mod123"
        ),
        str(del_file): FileChange(
            change_type=Change.deleted,
            path=str(del_file)
        )
    }
    
    report = await sync_service.sync(file_changes=changes)
    
    # Verify report contains all changes
    assert str(new_file) in report.new
    assert str(mod_file) in report.modified
    assert str(del_file) in report.deleted
    
    # Check checksums
    assert report.checksums[str(new_file)] == "new123"
    assert report.checksums[str(mod_file)] == "mod123"
    assert str(del_file) not in report.checksums


@pytest.mark.asyncio
async def test_sync_requires_params(sync_service):
    """Test sync requires either directory or file_changes"""
    with pytest.raises(ValueError):
        await sync_service.sync()


@pytest.mark.asyncio
async def test_sync_with_invalid_change_type(sync_service, tmp_path):
    """Test handling of invalid change types"""
    file_path = tmp_path / "test.md"
    file_path.touch()
    
    # Type checker won't let us create this directly, so ignore the type
    changes = {
        str(file_path): FileChange(
            change_type="invalid",  # type: ignore
            path=str(file_path),
            checksum="test123"
        )
    }
    
    with pytest.raises(Exception):
        await sync_service.sync(file_changes=changes)


@pytest.mark.asyncio
async def test_end_to_end_watch_sync(watch_service, sync_service, tmp_path):
    """Test complete watch -> sync flow"""
    # Create a test file that will trigger a watch event
    test_file = tmp_path / "test.md"
    test_file.write_text("""---
title: Test Note
type: note
---
# Test
Testing watch -> sync flow
""")
    
    # Simulate watchfiles event
    changes = {(Change.added, str(test_file))}
    await watch_service.handle_changes(changes)
    
    # Check watch service state
    assert watch_service.state.files_synced == 1
    assert len(watch_service.state.recent_events) == 1
    event = watch_service.state.recent_events[0]
    assert event.path == str(test_file)
    assert event.status == "success"
