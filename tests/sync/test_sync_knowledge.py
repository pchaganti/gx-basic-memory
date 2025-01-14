"""Test knowledge sync functionality."""

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
async def test_sync_knowledge(
    sync_service: SyncService, test_config: ProjectConfig, entity_service: EntityService
):
    """Test basic knowledge sync functionality."""
    # Create test files
    project_dir = test_config.home

    # New entity with relation
    new_content = """
---
type: knowledge
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
    await create_test_file(project_dir / "concept/test_concept.md", new_content)

    # Create related entity in DB that will be deleted
    other = Entity(
        permalink="concept/other",
        title="Other",
        entity_type="test",
        file_path="concept/other.md",
        checksum="12345678",
        content_type="text/markdown",
    )
    await entity_service.repository.add(other)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify results
    entities = await entity_service.repository.find_all()
    assert len(entities) == 1

    # Find new entity
    test_concept = next(e for e in entities if e.permalink == "concept/test_concept")
    assert test_concept.entity_type == "knowledge"

    # Verify relation was not created
    # because file for related entity was not found
    entity = await entity_service.get_by_permalink(test_concept.permalink)
    relations = entity.relations
    assert len(relations) == 0


@pytest.mark.asyncio
async def test_sync_entity_with_nonexistent_relations(
    sync_service: SyncService, test_config: ProjectConfig
):
    """Test syncing an entity that references nonexistent entities."""
    project_dir = test_config.home

    # Create entity that references entities we haven't created yet
    content = """
---
type: knowledge
id: concept/depends_on_future
created: 2024-01-01
modified: 2024-01-01
---
# Test Dependencies

## Observations
- [design] Testing future dependencies

## Relations
- depends_on [[concept/not_created_yet]]
- uses [[concept/also_future]]
"""
    await create_test_file(project_dir / "concept/depends_on_future.md", content)

    # Sync
    await sync_service.sync(test_config.home)

    # Verify entity created but no relations
    entity = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/depends_on_future"
    )
    assert entity is not None
    assert len(entity.relations) == 0  # Relations to nonexistent entities should be skipped


@pytest.mark.asyncio
async def test_sync_entity_circular_relations(
    sync_service: SyncService, test_config: ProjectConfig
):
    """Test syncing entities with circular dependencies."""
    project_dir = test_config.home

    # Create entity A that depends on B
    content_a = """
---
type: knowledge
id: concept/entity_a
created: 2024-01-01
modified: 2024-01-01
---
# Entity A

## Observations
- First entity in circular reference

## Relations
- depends_on [[concept/entity_b]]
"""
    await create_test_file(project_dir / "concept/entity_a.md", content_a)

    # Create entity B that depends on A
    content_b = """
---
type: knowledge
id: concept/entity_b
created: 2024-01-01
modified: 2024-01-01
---
# Entity B

## Observations
- Second entity in circular reference

## Relations
- depends_on [[concept/entity_a]]
"""
    await create_test_file(project_dir / "concept/entity_b.md", content_b)

    # Sync
    await sync_service.sync(test_config.home)

    # Verify both entities and their relations
    entity_a = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/entity_a"
    )
    entity_b = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/entity_b"
    )

    # outgoing relations
    assert len(entity_a.outgoing_relations) == 1
    assert len(entity_b.outgoing_relations) == 1

    # incoming relations
    assert len(entity_a.incoming_relations) == 1
    assert len(entity_b.incoming_relations) == 1

    # all relations
    assert len(entity_a.relations) == 2
    assert len(entity_b.relations) == 2

    # Verify circular reference works
    a_relation = entity_a.outgoing_relations[0]
    assert a_relation.to_id == entity_b.id

    b_relation = entity_b.outgoing_relations[0]
    assert b_relation.to_id == entity_a.id


@pytest.mark.asyncio
async def test_sync_entity_duplicate_relations(
    sync_service: SyncService, test_config: ProjectConfig
):
    """Test handling of duplicate relations in an entity."""
    project_dir = test_config.home

    # Create target entity first
    target_content = """
---
type: knowledge
id: concept/target
created: 2024-01-01
modified: 2024-01-01
---
# Target Entity

## Observations
- something to observe

"""
    await create_test_file(project_dir / "concept/target.md", target_content)

    # Create entity with duplicate relations
    content = """
---
type: knowledge
id: concept/duplicate_relations
created: 2024-01-01
modified: 2024-01-01
---
# Test Duplicates

## Observations
- this has a lot of relations

## Relations
- depends_on [[concept/target]]
- depends_on [[concept/target]]  # Duplicate
- uses [[concept/target]]  # Different relation type
- uses [[concept/target]]  # Duplicate of different type
"""
    await create_test_file(project_dir / "concept/duplicate_relations.md", content)

    # Sync
    await sync_service.sync(test_config.home)

    # Verify duplicates are handled
    entity = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/duplicate_relations"
    )

    # Count relations by type
    relation_counts = {}
    for rel in entity.relations:
        relation_counts[rel.relation_type] = relation_counts.get(rel.relation_type, 0) + 1

    # Should only have one of each type
    assert relation_counts["depends_on"] == 1
    assert relation_counts["uses"] == 1


@pytest.mark.asyncio
async def test_sync_entity_with_invalid_category(
    sync_service: SyncService, test_config: ProjectConfig
):
    """Test handling of invalid observation categories."""
    project_dir = test_config.home

    content = """
---
type: knowledge
id: concept/invalid_category
created: 2024-01-01
modified: 2024-01-01
---
# Test Categories

## Observations
- [invalid_category] This is fine
- [not_a_real_category] Should default to note
- This one is not an observation, should be ignored
- [design] This is valid 
"""
    await create_test_file(project_dir / "concept/invalid_category.md", content)

    # Sync
    await sync_service.sync(test_config.home)

    # Verify observations
    entity = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/invalid_category"
    )

    assert len(entity.observations) == 3
    categories = [obs.category for obs in entity.observations]

    # Invalid categories should be converted to default
    assert "note" in categories
    # Valid categories preserved
    assert "design" in categories


@pytest.mark.asyncio
async def test_sync_entity_with_order_dependent_relations(
    sync_service: SyncService, test_config: ProjectConfig
):
    """Test that order of entity syncing doesn't affect relation creation."""
    project_dir = test_config.home

    # Create several interrelated entities
    entities = {
        "a": """
---
type: knowledge
id: concept/entity_a
created: 2024-01-01
modified: 2024-01-01
---
# Entity A

## Observations
- depends on b
- depends on c

## Relations
- depends_on [[concept/entity_b]]
- depends_on [[concept/entity_c]]
""",
        "b": """
---
type: knowledge
id: concept/entity_b
created: 2024-01-01
modified: 2024-01-01
---
# Entity B

## Observations
- depends on c

## Relations
- depends_on [[concept/entity_c]]
""",
        "c": """
---
type: knowledge
id: concept/entity_c
created: 2024-01-01
modified: 2024-01-01
---
# Entity C

## Observations
- depends on a

## Relations
- depends_on [[concept/entity_a]]
""",
    }

    # Create files in different orders and verify results are the same
    for name, content in entities.items():
        await create_test_file(project_dir / f"concept/entity_{name}.md", content)

    # Sync
    await sync_service.sync(test_config.home)

    # Verify all relations are created correctly regardless of order
    entity_a = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/entity_a"
    )
    entity_b = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/entity_b"
    )
    entity_c = await sync_service.entity_sync_service.entity_repository.get_by_permalink(
        "concept/entity_c"
    )

    assert len(entity_a.outgoing_relations) == 2  # Should depend on B and C
    assert len(entity_a.incoming_relations) == 1  # C depends on A

    assert len(entity_b.outgoing_relations) == 1  # Should depend on C
    assert len(entity_b.incoming_relations) == 1  # A depends on B

    assert len(entity_c.outgoing_relations) == 1  # Should depend on A
    assert len(entity_c.incoming_relations) == 2  # A and B depend on C
