"""Test general sync behavior."""

import asyncio
from pathlib import Path
import pytest
import pytest_asyncio

from basic_memory.config import ProjectConfig
from basic_memory.services import DocumentService, EntityService, FileChangeScanner
from basic_memory.services.sync.knowledge_sync_service import KnowledgeSyncService
from basic_memory.services.sync.sync_service import SyncService
from basic_memory.markdown import KnowledgeParser
from basic_memory.models import Document, Entity, Observation


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_empty_directories(
    sync_service: SyncService,
    test_config: ProjectConfig
):
    """Test syncing empty directories."""
    await sync_service.sync(test_config.home)
    
    # Should not raise exceptions for empty dirs
    assert (test_config.documents_dir).exists()
    assert (test_config.knowledge_dir).exists()


@pytest.mark.asyncio
async def test_sync_file_modified_during_sync(
    sync_service: SyncService,
    test_config: ProjectConfig
):
    """Test handling of files that change during sync process."""
    # Create initial files
    doc_path = test_config.documents_dir / "changing.md"
    await create_test_file(doc_path, "Initial content")

    # Setup async modification during sync
    async def modify_file():
        await asyncio.sleep(0.1)  # Small delay to ensure sync has started
        doc_path.write_text("Modified during sync")

    # Run sync and modification concurrently
    await asyncio.gather(
        sync_service.sync(test_config.home),
        modify_file()
    )

    # Verify final state
    doc = await sync_service.document_service.repository.find_by_path_id("changing.md")
    assert doc is not None
    # File should have a checksum, even if it's from either version
    assert doc.checksum is not None


@pytest.mark.asyncio
async def test_sync_null_checksum_cleanup(
    sync_service: SyncService,
    test_config: ProjectConfig,
    entity_service: EntityService
):
    """Test handling of entities with null checksums from incomplete syncs."""
    # Create entity with null checksum (simulating incomplete sync)
    entity = Entity(
        path_id="concept/incomplete",
        name="Incomplete",
        entity_type="concept",
        file_path="concept/incomplete.md",
        checksum=None  # Null checksum
    )
    await entity_service.repository.add(entity)

    # Create corresponding file
    content = """
---
type: concept
id: concept/incomplete
created: 2024-01-01
modified: 2024-01-01
---
# Incomplete Entity

## Observations
- Testing cleanup
"""
    await create_test_file(test_config.knowledge_dir / "concept/incomplete.md", content)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify entity was properly synced
    updated = await entity_service.get_by_path_id("concept/incomplete")
    assert updated.checksum is not None


@pytest.mark.asyncio
async def test_sync_mixed_document_types(
    sync_service: SyncService,
    test_config: ProjectConfig
):
    """Test handling documents and knowledge files with similar paths."""
    # Create a document
    doc_content = "# Regular Document"
    await create_test_file(test_config.documents_dir / "test.md", doc_content)

    # Create a knowledge file
    knowledge_content = """
---
type: concept
id: concept/test
created: 2024-01-01
modified: 2024-01-01
---
# Knowledge File

## Observations
- This is a test
"""
    await create_test_file(test_config.knowledge_dir / "concept/test.md", knowledge_content)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify both types exist correctly
    doc = await sync_service.document_service.repository.find_by_path_id("test.md")
    assert doc is not None

    entity = await sync_service.knowledge_sync_service.entity_service.get_by_path_id("concept/test")
    assert entity is not None
    assert len(entity.observations) == 1


@pytest.mark.asyncio
async def test_sync_performance_large_files(
    sync_service: SyncService,
    test_config: ProjectConfig
):
    """Test sync performance with larger files."""
    # Create a large document with many lines
    large_doc = ["Line " + str(i) for i in range(1000)]
    await create_test_file(
        test_config.documents_dir / "large.md",
        "\n".join(large_doc)
    )

    # Create a knowledge file with many observations
    observations = [f"- Observation {i}" for i in range(100)]
    knowledge_content = f"""
---
type: concept
id: concept/large
created: 2024-01-01
modified: 2024-01-01
---
# Large Entity

## Observations
{chr(10).join(observations)}
"""
    await create_test_file(test_config.knowledge_dir / "concept/large.md", knowledge_content)

    # Time the sync
    start_time = asyncio.get_event_loop().time()
    await sync_service.sync(test_config.home)
    duration = asyncio.get_event_loop().time() - start_time

    # Verify everything synced
    doc = await sync_service.document_service.repository.find_by_path_id("large.md")
    assert doc is not None

    entity = await sync_service.knowledge_sync_service.entity_service.get_by_path_id("concept/large")
    assert entity is not None
    assert len(entity.observations) == 100

    # Basic performance check - should sync in reasonable time
    assert duration < 5  # Should complete in under 5 seconds


@pytest.mark.asyncio
async def test_sync_concurrent_updates(
    sync_service: SyncService,
    test_config: ProjectConfig
):
    """Test handling multiple concurrent sync operations."""
    # Create initial files
    doc1_path = test_config.documents_dir / "doc1.md"
    doc2_path = test_config.documents_dir / "doc2.md"
    
    await create_test_file(doc1_path, "Doc 1 content")
    await create_test_file(doc2_path, "Doc 2 content")

    # Run multiple syncs concurrently
    results = await asyncio.gather(
        sync_service.sync(test_config.home),
        sync_service.sync(test_config.home),
        return_exceptions=True
    )

    # Check no exceptions were raised
    for r in results:
        assert not isinstance(r, Exception)

    # Verify final state
    docs = await sync_service.document_service.repository.find_all()
    assert len(docs) == 2
    assert {d.path_id for d in docs} == {"doc1.md", "doc2.md"}