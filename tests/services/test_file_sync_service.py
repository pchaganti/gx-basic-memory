"""Test file sync service."""
import pytest
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory.repository import DocumentRepository, EntityRepository
from basic_memory.services import FileSyncService
from basic_memory.utils.file_utils import compute_checksum
from basic_memory.models import Document



@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create temp directory for test files."""
    return tmp_path



async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_scan_empty_directory(
    file_sync_service: FileSyncService,
    temp_dir: Path
):
    """Test scanning empty directory."""
    files = await file_sync_service.scan_directory(temp_dir)
    assert len(files) == 0


@pytest.mark.asyncio
async def test_scan_with_mixed_files(
    file_sync_service: FileSyncService,
    temp_dir: Path
):
    """Test scanning directory with markdown and non-markdown files."""
    # Create test files
    await create_test_file(temp_dir / "doc.md", "markdown")
    await create_test_file(temp_dir / "text.txt", "not markdown")
    await create_test_file(temp_dir / "notes/deep.md", "nested markdown")

    files = await file_sync_service.scan_directory(temp_dir)
    assert len(files) == 2
    assert "doc.md" in files
    assert "notes/deep.md" in files
    assert "text.txt" not in files


@pytest.mark.asyncio
async def test_detect_new_files(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    document_repository: DocumentRepository
):
    """Test detection of new files."""
    # Create new file
    await create_test_file(temp_dir / "new.md")
    
    changes = await file_sync_service.find_changes(
        directory=temp_dir,
        get_records=document_repository.find_all
    )
    
    assert len(changes.new) == 1
    assert "new.md" in changes.new


@pytest.mark.asyncio
async def test_detect_modified_file(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    document_repository: DocumentRepository
):
    """Test detection of modified files."""
    path = "test.md"
    content = "original"
    await create_test_file(temp_dir / path, content)
    
    # Add to DB
    doc = Document(
        path_id=path,
        file_path=path,
        checksum=await compute_checksum(content)
    )
    await document_repository.add(doc)

    # Modify file
    await create_test_file(temp_dir / path, "modified")

    changes = await file_sync_service.find_changes(
        directory=temp_dir,
        get_records=document_repository.find_all
    )

    assert len(changes.modified) == 1
    assert path in changes.modified


@pytest.mark.asyncio
async def test_detect_moved_file(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    document_repository: DocumentRepository
):
    """Test detection of file moves (including case changes)."""
    original_path = "Original.md"
    new_path = "new_location/Original.md"
    content = "test content"
    checksum = await compute_checksum(content)

    # Add original to DB
    doc = Document(
        path_id=original_path,
        file_path=original_path,
        checksum=checksum
    )
    await document_repository.add(doc)

    # Create file in new location
    await create_test_file(temp_dir / new_path, content)

    changes = await file_sync_service.find_changes(
        directory=temp_dir,
        get_records=document_repository.find_all
    )

    assert len(changes.moved) == 1
    assert new_path in changes.moved
    assert changes.moved[new_path].moved_from == original_path


@pytest.mark.asyncio
async def test_detect_deleted_files(
    file_sync_service: FileSyncService,
    temp_dir: Path,
    document_repository: DocumentRepository
):
    """Test detection of deleted files."""
    path = "deleted.md"
    
    # Add to DB but don't create file
    doc = Document(
        path_id=path,
        file_path=path,
        checksum="any-checksum"
    )
    await document_repository.add(doc)

    changes = await file_sync_service.find_changes(
        directory=temp_dir,
        get_records=document_repository.find_all
    )

    assert len(changes.deleted) == 1
    assert path in changes.deleted