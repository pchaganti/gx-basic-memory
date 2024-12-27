"""Tests for file sync service."""

import asyncio
from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory import db
from basic_memory.repository import DocumentRepository, EntityRepository
from basic_memory.services import FileSyncService
from basic_memory.utils.file_utils import compute_checksum

@pytest_asyncio.fixture
def temp_dir(test_config):
    return test_config.home


@pytest.mark.asyncio
async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

@pytest.mark.asyncio
async def test_scan_directory_empty(
    file_sync_service: FileSyncService,
    temp_dir: Path
):
    """Test scanning empty directory."""
    files = await file_sync_service.scan_directory(temp_dir)
    assert len(files) == 0

@pytest.mark.asyncio
async def test_scan_directory_with_files(
    file_sync_service: FileSyncService,
    temp_dir: Path
):
    """Test scanning directory with markdown files."""
    # Create test files
    await create_test_file(temp_dir / "test1.md", "content 1")
    await create_test_file(temp_dir / "test2.md", "content 2")
    await create_test_file(temp_dir / "not-markdown.txt", "ignore me")

    files = await file_sync_service.scan_directory(temp_dir)
    assert len(files) == 2
    assert "test1.md" in files
    assert "test2.md" in files
    assert "not-markdown.txt" not in files

@pytest.mark.asyncio
async def test_find_new_files(
    file_sync_service: FileSyncService,
    temp_dir: Path
):
    """Test detection of new files."""
    # Create new file
    await create_test_file(temp_dir / "new_file.md", "new content")

    changes = await file_sync_service.find_changes(
        directory=temp_dir,
        get_records=lambda: asyncio.sleep(0, [])  # Empty DB
    )
    
    assert len(changes.new) == 1
    assert "new_file.md" in changes.new
    assert len(changes.modified) == 0
    assert len(changes.deleted) == 0
    assert len(changes.moved) == 0

@pytest.mark.asyncio
async def test_find_case_sensitive_move(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    session_maker: AsyncGenerator[AsyncSession, None]
):
    """Test detection of case-sensitive file moves."""
    # Create and track original file
    original_path = "Original.md"
    await create_test_file(temp_dir / original_path, "test content")
    original_checksum = await compute_checksum("test content")
    
    # Add to DB with original path
    async with db.scoped_session(session_maker) as session:
        await session.execute(text(
            f"INSERT INTO document (path_id, file_path, checksum) VALUES ('{original_path.lower()}', '{original_path}', '{original_checksum}')"))
        await session.commit()

        # Rename file (case change only)
        new_path = "ORIGINAL.md"
        (temp_dir / original_path).rename(temp_dir / new_path)
    
        async def get_records():
            return session.execute(
                text("SELECT * FROM document")
            ).fetchall()

        changes = await file_sync_service.find_changes(
            directory=temp_dir,
            get_records=(await get_records),
            normalize_path=lambda p: p.lower()
        )

    assert len(changes.moved) == 1
    assert new_path in changes.moved
    assert changes.moved[new_path].moved_from == original_path
    assert len(changes.new) == 0
    assert len(changes.modified) == 0
    assert len(changes.deleted) == 0




@pytest.mark.asyncio
async def test_find_modified_files(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    session_maker: AsyncGenerator[AsyncSession, None]
):
    """Test detection of modified files."""
    # Create and track original file
    path = "test.md"
    await create_test_file(temp_dir / path, "original content")
    original_checksum = await compute_checksum("original content")
    
    # Add to DB
    async with db.scoped_session(session_maker) as session:
        await session.execute(
            "INSERT INTO document (path_id, file_path, checksum) VALUES (?, ?, ?)",
            [path.lower(), path, original_checksum]
        )
        await session.commit()

        # Modify file
        await create_test_file(temp_dir / path, "modified content")
    
        changes = await file_sync_service.find_changes(
            directory=temp_dir,
            get_records=lambda: session.execute(
                "SELECT * FROM document"
            ).fetchall(),
            normalize_path=lambda p: p.lower()
        )

    assert len(changes.modified) == 1
    assert path in changes.modified
    assert len(changes.new) == 0
    assert len(changes.deleted) == 0
    assert len(changes.moved) == 0

@pytest.mark.asyncio
async def test_find_deleted_files(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    session_maker: AsyncGenerator[AsyncSession, None]
):
    """Test detection of deleted files."""
    # Add file to DB that doesn't exist
    missing_path = "deleted.md"
    async with db.scoped_session(session_maker) as session:
        await session.execute(
            "INSERT INTO document (path_id, file_path, checksum) VALUES (?, ?, ?)",
            [missing_path.lower(), missing_path, "any-checksum"]
        )
        await session.commit()

        changes = await file_sync_service.find_changes(
            directory=temp_dir,
            get_records=lambda: session.execute(
                "SELECT * FROM document"
            ).fetchall(),
            normalize_path=lambda p: p.lower()
        )

    assert len(changes.deleted) == 1
    assert missing_path in changes.deleted
    assert len(changes.new) == 0
    assert len(changes.modified) == 0
    assert len(changes.moved) == 0

@pytest.mark.asyncio
async def test_path_normalization(
    file_sync_service: FileSyncService,
    temp_dir: Path
):
    """Test path normalization for different formats."""
    paths = [
        ("my file.md", "my_file"),          # Spaces
        ("MyFile.md", "myfile"),            # Case
        ("my/file.md", "my/file"),          # Subdirectories
        ("MY/FILE.md", "my/file"),          # Mixed case dirs
        ("my//file.md", "my/file"),         # Extra slashes
        ("./my/file.md", "my/file"),        # Current dir
    ]

    for file_path, expected_norm in paths:
        norm_path = file_sync_service.normalize_path(file_path)
        assert norm_path == expected_norm, f"Failed to normalize {file_path}"