"""Tests for the watch service."""

import pytest
import pytest_asyncio
from datetime import datetime
from watchfiles import Change

from basic_memory.sync.watch_service import WatchServiceState


@pytest_asyncio.fixture
async def sample_markdown_file(test_config):
    content = """---
title: Test Note
type: note
---
# Test Note
This is a test note.
"""
    file_path = test_config.home / "test.md"
    file_path.write_text(content)
    return file_path


@pytest.mark.asyncio
async def test_handle_file_added(test_config, watch_service, sync_service, sample_markdown_file):
    """Test handling a new file event"""

    await watch_service.handle_changes(test_config.home)

    # Check stats updated
    assert watch_service.state.synced_files == 1
    assert watch_service.state.last_scan is not None

    # Check event recorded
    assert len(watch_service.state.recent_events) == 1
    event = watch_service.state.recent_events[0]
    assert event.path == "test.md"
    assert event.action == "new"
    assert event.status == "success"


@pytest.mark.asyncio
async def test_handle_file_modified(test_config, watch_service, sync_service, sample_markdown_file):
    """Test handling a modified file event"""
    # First add the file
    await watch_service.handle_changes(test_config.home)

    # Modify the file
    sample_markdown_file.write_text(sample_markdown_file.read_text() + "\nModified content")
    await watch_service.handle_changes(test_config.home)

    # Should have two events
    assert len(watch_service.state.recent_events) == 2
    assert watch_service.state.synced_files == 1
    event = watch_service.state.recent_events[0]
    assert event.path == "test.md"
    assert event.action == "modified"
    assert event.status == "success"


@pytest.mark.asyncio
async def test_handle_file_moved(test_config, watch_service, sync_service, sample_markdown_file):
    """Test handling a moved file event"""
    # First add the file
    await watch_service.handle_changes(test_config.home)

    # Modify the file
    renamed = sample_markdown_file.rename(test_config.home / "moved.md")

    await watch_service.handle_changes(test_config.home)

    # Should have two events
    assert len(watch_service.state.recent_events) == 2
    assert watch_service.state.synced_files == 1
    event = watch_service.state.recent_events[0]
    assert event.path == "test.md -> moved.md"
    assert event.action == "moved"
    assert event.status == "success"


@pytest.mark.asyncio
async def test_handle_file_deleted(test_config, watch_service, sync_service, sample_markdown_file):
    """Test handling a deleted file event"""
    # First add the file
    await watch_service.handle_changes(test_config.home)

    # Delete the file
    sample_markdown_file.unlink()
    await watch_service.handle_changes(test_config.home)

    # Should have two events
    assert len(watch_service.state.recent_events) == 2
    delete_event = watch_service.state.recent_events[0]
    assert delete_event.action == "deleted"
    assert delete_event.path == "test.md"


@pytest.mark.asyncio
async def test_filter_changes(watch_service):
    """Test change filtering"""
    assert watch_service.filter_changes(Change.added, "test.md") is True
    assert watch_service.filter_changes(Change.added, "test.txt") is False
    assert watch_service.filter_changes(Change.added, ".test.md") is False


@pytest.mark.asyncio
async def test_recent_events_limit(watch_service):
    """Test that recent events are limited to 100"""
    for i in range(150):
        watch_service.state.add_event(path=f"test{i}.md", action="sync", status="success")

    assert len(watch_service.state.recent_events) == 100
    # Most recent should be at the start
    assert watch_service.state.recent_events[0].path == "test149.md"


@pytest.mark.asyncio
async def test_state_serialization(watch_service):
    """Test state serializes to dict correctly"""
    # Add some test state
    watch_service.state.running = True
    watch_service.state.add_event(path="test.md", action="sync", status="success")

    data = WatchServiceState.model_dump(watch_service.state)

    # Check basic fields
    assert data["running"] is True
    assert isinstance(data["start_time"], datetime)

    # Check events serialized
    assert len(data["recent_events"]) == 1
    event = data["recent_events"][0]
    assert event["path"] == "test.md"
    assert event["action"] == "sync"
    assert isinstance(event["timestamp"], datetime)


@pytest.mark.asyncio
async def test_status_file(watch_service, tmp_path):
    """Test status file writing"""
    watch_service.state.running = True
    await watch_service.write_status()

    status_file = watch_service.status_path
    assert status_file.exists()

    # Should be valid JSON with our fields
    import json

    data = json.loads(status_file.read_text())
    assert data["running"] is True
    assert isinstance(data["start_time"], str)
    assert data["pid"] > 0
