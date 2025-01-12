"""Test general sync behavior."""

import asyncio
from pathlib import Path

import pytest

from basic_memory.config import ProjectConfig
from basic_memory.models import Entity
from basic_memory.services import EntityService
from basic_memory.sync.sync_service import SyncService


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_empty_directories(sync_service: SyncService, test_config: ProjectConfig):
    """Test syncing empty directories."""
    await sync_service.sync(test_config.home)

    # Should not raise exceptions for empty dirs
    assert (test_config.home).exists()


@pytest.mark.asyncio
async def test_sync_file_modified_during_sync(
    sync_service: SyncService, test_config: ProjectConfig
):
    """Test handling of files that change during sync process."""
    # Create initial files
    doc_path = test_config.home / "changing.md"
    await create_test_file(
        doc_path,
        """
---
type: knowledge
id: changing
created: 2024-01-01
modified: 2024-01-01
---
# Knowledge File

## Observations
- This is a test
""",
    )

    # Setup async modification during sync
    async def modify_file():
        await asyncio.sleep(0.1)  # Small delay to ensure sync has started
        doc_path.write_text("Modified during sync")

    # Run sync and modification concurrently
    await asyncio.gather(sync_service.sync(test_config.home), modify_file())

    # Verify final state
    doc = await sync_service.knowledge_sync_service.entity_repository.get_by_permalink("changing")
    assert doc is not None
    # File should have a checksum, even if it's from either version
    assert doc.checksum is not None


@pytest.mark.asyncio
async def test_sync_null_checksum_cleanup(
    sync_service: SyncService, test_config: ProjectConfig, entity_service: EntityService
):
    """Test handling of entities with null checksums from incomplete syncs."""
    # Create entity with null checksum (simulating incomplete sync)
    entity = Entity(
        permalink="concept/incomplete",
        title="Incomplete",
        entity_type="test",
        file_path="concept/incomplete.md",
        checksum=None,  # Null checksum
        content_type="text/markdown",
    )
    await entity_service.repository.add(entity)

    # Create corresponding file
    content = """
---
type: knowledge
id: concept/incomplete
created: 2024-01-01
modified: 2024-01-01
---
# Incomplete Entity

## Observations
- Testing cleanup
"""
    await create_test_file(test_config.home / "concept/incomplete.md", content)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify entity was properly synced
    updated = await entity_service.get_by_permalink("concept/incomplete")
    assert updated.checksum is not None
