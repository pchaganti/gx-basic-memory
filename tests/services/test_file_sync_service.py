"""Tests for FileSyncService."""

from pathlib import Path

import pytest
import pytest_asyncio

from basic_memory.services.file_sync_service import FileSyncService


@pytest_asyncio.fixture
async def file_sync_service(document_repository, entity_repository) -> FileSyncService:
    """Create FileSyncService instance."""
    return FileSyncService(document_repository, entity_repository)


@pytest_asyncio.fixture
async def knowledge_dir(test_config) -> Path:
    """Get knowledge directory."""
    test_config.knowledge_dir.mkdir(parents=True)
    return test_config.knowledge_dir


@pytest_asyncio.fixture
async def docs_dir(test_config) -> Path:
    """Get documents directory."""
    test_config.documents_dir.mkdir(parents=True)
    return test_config.documents_dir


@pytest_asyncio.fixture
async def sample_documents(docs_dir) -> dict[str, str]:
    """Create sample document files.
    Note: These have .md extension in filesystem but should be stripped in results.
    """
    design_dir = docs_dir / "design"
    notes_dir = docs_dir / "notes"
    design_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)

    files = {
        # Keys don't include .md to match expected results
        "design/architecture": "# Architecture\nDesign notes",
        "notes/meeting": "# Meeting\nNotes from discussion",
        "README": "# Project\nOverview"
    }

    for rel_path, content in files.items():
        full_path = docs_dir / f"{rel_path}.md"
        full_path.write_text(content)

    return files


@pytest_asyncio.fixture
async def sample_knowledge(knowledge_dir) -> dict[str, str]:
    """Create sample knowledge files.
    Note: These have .md extension in filesystem but should be stripped in results.
    """
    component_dir = knowledge_dir / "component"
    concept_dir = knowledge_dir / "concept"
    component_dir.mkdir(parents=True, exist_ok=True)
    concept_dir.mkdir(parents=True, exist_ok=True)

    files = {
        # Keys don't include .md to match expected results
        "component/memory_service": "# Memory Service\nCore service",
        "component/file_service": "# File Service\nFile ops",
        "concept/local_first": "# Local First\nDesign principle"
    }

    for rel_path, content in files.items():
        full_path = knowledge_dir / f"{rel_path}.md"
        full_path.write_text(content)

    return files


@pytest.mark.asyncio
async def test_scan_directory(file_sync_service, docs_dir, sample_documents):
    """Test scanning directory for files."""
    # Scan documents directory
    scanned = await file_sync_service.scan_directory(docs_dir)

    # Should find all files and strip .md extension
    assert len(scanned) == len(sample_documents)
    assert set(scanned.keys()) == set(sample_documents.keys())  # No .md in paths
    assert all(isinstance(checksum, str) for checksum in scanned.values())

    # Checksums should be different for different content
    checksums = list(scanned.values())
    assert len(set(checksums)) == len(checksums)  # All unique

    # File paths should not have .md extension
    assert not any(path.endswith(".md") for path in scanned.keys())


@pytest.mark.asyncio
async def test_document_changes_new_files(file_sync_service, docs_dir, sample_documents):
    """Test detecting new document files."""
    # Check changes - all should be new since DB is empty
    changes = await file_sync_service.find_document_changes(docs_dir)

    assert changes.new == set(sample_documents.keys())  # No .md in paths
    assert not changes.modified
    assert not changes.deleted


@pytest.mark.asyncio
async def test_document_changes_modified_files(
    file_sync_service, docs_dir, sample_documents, document_repository
):
    """Test detecting modified document files."""
    # Create initial DB records - without .md extension
    for path, content in sample_documents.items():
        await document_repository.create({
            "path": path,  # No .md
            "checksum": "old_checksum"  # Different from actual file
        })

    # Check changes - all should be modified
    changes = await file_sync_service.find_document_changes(docs_dir)

    assert not changes.new
    assert changes.modified == set(sample_documents.keys())  # No .md
    assert not changes.deleted


@pytest.mark.asyncio
async def test_document_changes_deleted_files(
    file_sync_service, docs_dir, document_repository
):
    """Test detecting deleted document files."""
    # Create DB records for non-existent files - without .md extension
    db_files = {
        "old/doc1": "checksum1",
        "old/doc2": "checksum2"
    }
    for path, checksum in db_files.items():
        await document_repository.create({
            "path": path,  # No .md
            "checksum": checksum
        })

    # Check changes - all should be deleted
    changes = await file_sync_service.find_document_changes(docs_dir)

    assert not changes.new
    assert not changes.modified
    assert changes.deleted == set(db_files.keys())  # No .md


@pytest.mark.asyncio
async def test_knowledge_changes_new_files(file_sync_service, knowledge_dir, sample_knowledge):
    """Test detecting new knowledge files."""
    # Check changes - all should be new since DB is empty
    changes = await file_sync_service.find_knowledge_changes(knowledge_dir)

    assert changes.new == set(sample_knowledge.keys())  # No .md
    assert not changes.modified
    assert not changes.deleted


@pytest.mark.asyncio
async def test_knowledge_changes_modified_files(
    file_sync_service, knowledge_dir, sample_knowledge, entity_repository
):
    """Test detecting modified knowledge files."""
    # Create initial DB records - without .md extension
    for path_id, content in sample_knowledge.items():
        await entity_repository.create({
            "path_id": path_id,  # No .md
            "name": path_id.split("/")[-1],
            "entity_type": path_id.split("/")[0],
            "checksum": "old_checksum"  # Different from actual file
        })

    # Check changes - all should be modified
    changes = await file_sync_service.find_knowledge_changes(knowledge_dir)

    assert not changes.new
    assert changes.modified == set(sample_knowledge.keys())  # No .md
    assert not changes.deleted


@pytest.mark.asyncio
async def test_knowledge_changes_deleted_files(
    file_sync_service, knowledge_dir, entity_repository
):
    """Test detecting deleted knowledge files."""
    # Create DB records for non-existent files - without .md extension
    db_files = {
        "component/old_service": "checksum1",
        "concept/old_idea": "checksum2"
    }
    for path_id, checksum in db_files.items():
        await entity_repository.create({
            "path_id": path_id,  # No .md
            "name": path_id.split("/")[-1],
            "entity_type": path_id.split("/")[0],
            "checksum": checksum
        })

    # Check changes - all should be deleted
    changes = await file_sync_service.find_knowledge_changes(knowledge_dir)

    assert not changes.new
    assert not changes.modified
    assert changes.deleted == set(db_files.keys())  # No .md