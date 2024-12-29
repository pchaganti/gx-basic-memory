"""Tests for knowledge sync service."""

import pytest
import pytest_asyncio
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory.services.sync.knowledge_sync_service import KnowledgeSyncService
from basic_memory.services import KnowledgeService, FileChangeScanner
from basic_memory.markdown import KnowledgeParser
from basic_memory.utils.file_utils import compute_checksum



pytestmark = pytest.mark.skip("Knowledge sync WIP")

@pytest_asyncio.fixture
async def knowledge_sync_service(
    file_sync_service: FileChangeScanner,  # from conftest
    knowledge_service: KnowledgeService,    # from conftest
    knowledge_parser: KnowledgeParser       # need to add to conftest
) -> KnowledgeSyncService:
    """Create knowledge sync service for testing."""
    return KnowledgeSyncService(file_sync_service, knowledge_service, knowledge_parser)


async def create_test_entity_file(
    path: Path, 
    entity_type: str = "test",
    name: str = "Test Entity",
    content: str = "test content"
) -> None:
    """Create a test entity file with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create basic entity markdown
    file_content = f"""---
type: {entity_type}
id: {entity_type}/{name.lower().replace(' ', '_')}
created: 2024-12-27T10:00:00Z
modified: 2024-12-27T10:00:00Z
tags: [test]
---

# {name}

{content}

## Observations
- [test] First observation #test
- [test] Second observation #test

## Relations
- relates_to [[Other_Entity]]
"""
    path.write_text(file_content)


@pytest.mark.asyncio
async def test_sync_new_entity(
    knowledge_sync_service: KnowledgeSyncService,
    test_config,
):
    """Test syncing a new entity file."""
    knowledge_dir = test_config.knowledge_dir
    test_file = knowledge_dir / "test" / "test_entity.md"
    
    # Create test file
    await create_test_entity_file(test_file)

    # Run sync
    changes = await knowledge_sync_service.sync(knowledge_dir)

    # Verify changes
    assert len(changes.new) == 1
    assert "test/test_entity.md" in changes.new

    # Verify entity in DB
    entity = await knowledge_sync_service.knowledge_service.get_entity_by_path_id("test/test_entity")
    assert entity.name == "Test Entity"
    assert entity.entity_type == "test"
    assert len(entity.observations) == 2
    assert len(entity.outbound_relations) == 1


@pytest.mark.asyncio
async def test_sync_modified_entity(
    knowledge_sync_service: KnowledgeSyncService,
    test_config,
    entity_repository,
):
    """Test syncing a modified entity file."""
    knowledge_dir = test_config.knowledge_dir
    test_file = knowledge_dir / "test" / "test_entity.md"
    
    # Create initial file and sync
    await create_test_entity_file(test_file)
    await knowledge_sync_service.sync(knowledge_dir)

    # Modify file
    await create_test_entity_file(
        test_file,
        content="modified content",
        name="Test Entity"  # Keep same name/path
    )

    # Run sync again
    changes = await knowledge_sync_service.sync(knowledge_dir)

    # Verify changes
    assert len(changes.modified) == 1
    assert "test/test_entity.md" in changes.modified

    # Verify entity updated
    entity = await knowledge_sync_service.knowledge_service.get_entity_by_path_id("test/test_entity")
    assert "modified content" in entity.description


@pytest.mark.asyncio
async def test_sync_moved_entity(
    knowledge_sync_service: KnowledgeSyncService,
    test_config,
    entity_repository
):
    """Test syncing a moved entity file."""
    knowledge_dir = test_config.knowledge_dir
    original_file = knowledge_dir / "test" / "original.md"
    new_file = knowledge_dir / "test" / "moved.md"
    
    # Create initial file and sync
    await create_test_entity_file(original_file, name="Original")
    await knowledge_sync_service.sync(knowledge_dir)

    # Create new file with same content
    new_file.parent.mkdir(parents=True, exist_ok=True)
    await create_test_entity_file(new_file, name="Moved")
    original_file.unlink()

    # Run sync
    changes = await knowledge_sync_service.sync(knowledge_dir)

    # Verify changes
    assert len(changes.moved) == 1
    assert "test/moved.md" in changes.moved
    assert changes.moved["test/moved.md"].moved_from == "test/original.md"

    # Verify entity updated
    with pytest.raises(Exception):
        # Original should be gone
        await knowledge_sync_service.knowledge_service.get_entity_by_path_id("test/original")

    # New entity should exist
    entity = await knowledge_sync_service.knowledge_service.get_entity_by_path_id("test/moved")
    assert entity.name == "Moved"
    assert len(entity.observations) == 2
    assert len(entity.outbound_relations) == 1


@pytest.mark.asyncio
async def test_sync_deleted_entity(
    knowledge_sync_service: KnowledgeSyncService,
    test_config,
    entity_repository
):
    """Test syncing a deleted entity file."""
    knowledge_dir = test_config.knowledge_dir
    test_file = knowledge_dir / "test" / "to_delete.md"
    
    # Create initial file and sync
    await create_test_entity_file(test_file)
    await knowledge_sync_service.sync(knowledge_dir)

    # Delete file
    test_file.unlink()

    # Run sync
    changes = await knowledge_sync_service.sync(knowledge_dir)

    # Verify changes
    assert len(changes.deleted) == 1
    assert "test/to_delete.md" in changes.deleted

    # Verify entity deleted
    with pytest.raises(Exception):
        await knowledge_sync_service.knowledge_service.get_entity_by_path_id("test/to_delete")