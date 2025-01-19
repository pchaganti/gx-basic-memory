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
permalink: concept/test_concept
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
    # because file was not found
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
permalink: concept/depends_on_future
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
permalink: concept/entity_a
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
permalink: concept/entity_b
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
permalink: concept/target
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
permalink: concept/duplicate_relations
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
permalink: concept/invalid_category
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
permalink: concept/entity_a
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
permalink: concept/entity_b
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
permalink: concept/entity_c
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
    doc = await sync_service.entity_sync_service.entity_repository.get_by_permalink("changing")
    assert doc is not None
    # File should have a checksum, even if it's from either version
    assert doc.checksum is not None
    
@pytest.mark.asyncio
async def test_permalink_formatting(sync_service: SyncService, test_config: ProjectConfig, entity_service: EntityService):
    """Test that permalinks are properly formatted during sync."""
    
    # Test cases with different filename formats
    test_files = {
    # filename -> expected permalink
    "my_awesome_feature.md": "my-awesome-feature",
    "MIXED_CASE_NAME.md": "mixed-case-name",
    "spaces and_underscores.md": "spaces-and-underscores",
    "design/model_refactor.md": "design/model-refactor",
    "test/multiple_word_directory/feature_name.md": "test/multiple-word-directory/feature-name",
    }
    
    # Create test files
    for filename, _ in test_files.items():
        content: str = """
---
type: knowledge
created: 2024-01-01
modified: 2024-01-01
---
# Test File

Testing permalink generation.
"""
        await create_test_file(test_config.home / filename, content)
        
        # Run sync
        await sync_service.sync(test_config.home)
        
    # Verify permalinks
    entities = await entity_service.repository.find_all()
    for filename, expected_permalink in test_files.items():
        # Find entity for this file
        entity = next(e for e in entities if e.file_path == filename)
        assert entity.permalink == expected_permalink, f"File {filename} should have permalink {expected_permalink}"

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
