"""Test sync service."""

from pathlib import Path
import pytest

from basic_memory.config import ProjectConfig
from basic_memory.services import EntityService
from basic_memory.services.sync.sync_service import SyncService
from basic_memory.models import Entity


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_knowledge(
    sync_service: SyncService, test_config: ProjectConfig, entity_service: EntityService
):
    """Test syncing knowledge files."""
    # Create test files
    knowledge_dir = test_config.knowledge_dir

    # New entity with relation
    new_content = """
---
type: concept
id: concept/test_concept
created: 2023-01-01
modified: 2023-01-01
---
# Test Concept

A test concept.

## Observations
- [design] Core feature

## Relations
- depends_on [[concept/other]]
"""
    await create_test_file(knowledge_dir / "concept/test_concept.md", new_content)

    # Create related entity in DB
    # will be categorized as deleted
    other = Entity(
        path_id="concept/other",
        name="Other",
        entity_type="concept",
        file_path="concept/other.md",
        checksum="12345678",
    )
    await entity_service.repository.add(other)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify results
    entities = await entity_service.repository.find_all()
    assert len(entities) == 1

    # Find new entity
    test_concept: Entity = next(e for e in entities if e.path_id == "concept/test_concept")
    assert test_concept.entity_type == "concept"

    # Verify relation was not created
    # because file for related entity was not found
    entity = await entity_service.get_by_path_id(test_concept.path_id)
    relations = entity.relations
    assert len(relations) == 0
