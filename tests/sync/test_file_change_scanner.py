"""Test file sync service."""

from pathlib import Path

import pytest

from basic_memory.file_utils import compute_checksum
from basic_memory.models import Entity
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.file_change_scanner import FileState


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create temp directory for test files."""
    return tmp_path


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_scan_empty_directory(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test scanning empty directory."""
    result = await file_change_scanner.scan_directory(temp_dir)
    assert len(result.files) == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_scan_with_mixed_files(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test scanning directory with markdown and non-markdown files."""
    # Create test files
    await create_test_file(temp_dir / "doc.md", "markdown")
    await create_test_file(temp_dir / "text.txt", "not markdown")
    await create_test_file(temp_dir / "notes/deep.md", "nested markdown")

    result = await file_change_scanner.scan_directory(temp_dir)
    assert len(result.files) == 2
    assert "doc.md" in result.files
    assert "notes/deep.md" in result.files
    assert len(result.errors) == 0

    # Verify FileState objects
    assert isinstance(result.files["doc.md"], str)
    # checksum
    assert result.files["doc.md"] is not None


@pytest.mark.asyncio
async def test_scan_with_unreadable_file(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test scanning directory with an unreadable file."""
    # Create a file we'll make unreadable
    bad_file = temp_dir / "bad.md"
    await create_test_file(bad_file)
    bad_file.chmod(0o000)  # Remove all permissions

    result = await file_change_scanner.scan_directory(temp_dir)
    assert len(result.files) == 0
    assert len(result.errors) == 1
    assert "bad.md" in result.errors


@pytest.mark.asyncio
async def test_detect_new_files(
    file_change_scanner: FileChangeScanner,
    temp_dir: Path,
):
    """Test detection of new files."""
    # Create new file
    await create_test_file(temp_dir / "new.md")

    # Empty DB state
    db_records = await file_change_scanner.get_db_file_state([])

    changes = await file_change_scanner.find_changes(directory=temp_dir, db_file_state=db_records)

    assert len(changes.new) == 1
    assert "new.md" in changes.new


@pytest.mark.asyncio
async def test_detect_modified_file(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test detection of modified files."""
    file_path = "test.md"
    content = "original"
    await create_test_file(temp_dir / file_path, content)

    # Create DB state with original checksum
    original_checksum = await compute_checksum(content)
    db_records = {
        file_path: FileState(file_path=file_path, permalink="test", checksum=original_checksum)
    }

    # Modify file
    await create_test_file(temp_dir / file_path, "modified")

    changes = await file_change_scanner.find_changes(directory=temp_dir, db_file_state=db_records)

    assert len(changes.modified) == 1
    assert file_path in changes.modified


@pytest.mark.asyncio
async def test_detect_deleted_files(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test detection of deleted files."""
    file_path = "deleted.md"

    # Create DB state with file that doesn't exist
    db_records = {
        file_path: FileState(file_path=file_path, permalink="deleted", checksum="any-checksum")
    }

    changes = await file_change_scanner.find_changes(directory=temp_dir, db_file_state=db_records)

    assert len(changes.deleted) == 1
    assert file_path in changes.deleted


@pytest.mark.asyncio
async def test_get_db_state_entities(file_change_scanner: FileChangeScanner):
    """Test converting entity records to file states."""
    entity = Entity(permalink="concept/test", file_path="concept/test.md", checksum="test-checksum")

    db_records = await file_change_scanner.get_db_file_state([entity])

    assert len(db_records) == 1
    assert "concept/test.md" in db_records
    assert db_records["concept/test.md"].checksum == "test-checksum"


@pytest.mark.asyncio
async def test_empty_directory(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test handling empty/nonexistent directory."""
    nonexistent = temp_dir / "nonexistent"

    changes = await file_change_scanner.find_changes(directory=nonexistent, db_file_state={})

    assert changes.total_changes == 0
    assert not changes.new
    assert not changes.modified
    assert not changes.deleted


@pytest.mark.asyncio
async def test_detect_moved_file(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test detection of file moves."""
    # Create original file
    old_path = "original/test.md"
    new_path = "new/location/test.md"
    content = "test content"

    await create_test_file(temp_dir / old_path, content)
    original_checksum = await compute_checksum(content)

    # Set up DB state with original location
    db_records = {
        old_path: FileState(file_path=old_path, permalink="test", checksum=original_checksum)
    }

    # Move file to new location
    old_file = temp_dir / old_path
    new_file = temp_dir / new_path
    new_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.rename(new_file)

    # Check changes
    changes = await file_change_scanner.find_changes(directory=temp_dir, db_file_state=db_records)

    # Should detect as move
    assert len(changes.moves) == 1
    assert changes.moves[old_path] == new_path
    # Should not be in new or deleted
    assert old_path not in changes.new
    assert old_path not in changes.deleted
    assert new_path not in changes.new


@pytest.mark.asyncio
async def test_move_with_content_change(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test handling a file that is both moved and modified."""
    # Create original file
    old_path = "original/test.md"
    new_path = "new/location/test.md"
    content = "original content"

    await create_test_file(temp_dir / old_path, content)
    original_checksum = await compute_checksum(content)

    # Set up DB state with original location
    db_records = {
        old_path: FileState(file_path=old_path, permalink="test", checksum=original_checksum)
    }

    # Move file and change content
    old_file = temp_dir / old_path
    new_file = temp_dir / new_path
    new_file.parent.mkdir(parents=True, exist_ok=True)
    await create_test_file(new_file, "modified content")
    old_file.unlink()

    # Check changes
    changes = await file_change_scanner.find_changes(directory=temp_dir, db_file_state=db_records)

    # Should be treated as delete + new, not move
    assert old_path in changes.deleted
    assert new_path in changes.new
    assert len(changes.moves) == 0


@pytest.mark.asyncio
async def test_multiple_moves(file_change_scanner: FileChangeScanner, temp_dir: Path):
    """Test detecting multiple file moves at once."""
    # Create original files
    files = {"a/test1.md": "content1", "b/test2.md": "content2"}
    new_locations = {"a/test1.md": "new/test1.md", "b/test2.md": "new/nested/test2.md"}

    db_records = {}
    # Create files and DB state
    for old_path, content in files.items():
        await create_test_file(temp_dir / old_path, content)
        checksum = await compute_checksum(content)
        db_records[old_path] = FileState(
            file_path=old_path, permalink=old_path.replace(".md", ""), checksum=checksum
        )

    # Move all files
    for old_path, new_path in new_locations.items():
        old_file = temp_dir / old_path
        new_file = temp_dir / new_path
        new_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.rename(new_file)

    # Check changes
    changes = await file_change_scanner.find_changes(directory=temp_dir, db_file_state=db_records)

    # Should detect both moves
    assert len(changes.moves) == 2
    assert changes.moves["a/test1.md"] == "new/test1.md"
    assert changes.moves["b/test2.md"] == "new/nested/test2.md"
    assert not changes.new
    assert not changes.deleted
