"""Tests for EntitySyncService."""

from datetime import datetime

import pytest
import pytest_asyncio

from basic_memory.markdown.schemas import (
    EntityMarkdown,
    EntityContent,
    EntityFrontmatter,
    Observation as MarkdownObservation,
    Relation as MarkdownRelation,
)
from basic_memory.models import Entity as EntityModel
from basic_memory.sync.entity_sync_service import EntitySyncService


@pytest_asyncio.fixture
def test_frontmatter() -> EntityFrontmatter:
    """Create test frontmatter."""
    return EntityFrontmatter(
        title="Test Entity",
        type="knowledge",
        permalink="concept/test-entity",
        created=datetime.now(),
        modified=datetime.now(),
        tags=["test", "sync"],
    )


@pytest_asyncio.fixture
def test_content() -> EntityContent:
    """Create test content with observations and relations."""
    return EntityContent(
        content="A test entity description",
        observations=[
            MarkdownObservation(content="First observation"),
            MarkdownObservation(content="Second observation"),
        ],
        relations=[
            MarkdownRelation(type="depends_on", target="concept/other-entity"),
            MarkdownRelation(type="related_to", target="concept/another-entity"),
        ],
    )


@pytest_asyncio.fixture
def test_markdown(test_frontmatter, test_content) -> EntityMarkdown:
    """Create complete test markdown entity."""
    return EntityMarkdown(frontmatter=test_frontmatter, content=test_content)


@pytest.mark.asyncio
async def test_create_entity_without_relations(
        entity_sync_service: EntitySyncService, test_markdown: EntityMarkdown
):
    """Test first pass creation without relations."""
    # Create entity first pass
    entity = await entity_sync_service.create_entity_from_markdown("test.md", test_markdown)

    # Check basic fields
    assert entity.title == "Test Entity"
    assert entity.entity_type == "knowledge"
    assert entity.permalink == "concept/test-entity"
    assert entity.summary == "A test entity description"

    # Check observations
    assert len(entity.observations) == 2
    assert entity.observations[0].content == "First observation"
    assert entity.observations[1].content == "Second observation"

    # Check no relations added
    assert len(entity.relations) == 0

    # Check checksum is None (indicating incomplete sync)
    assert entity.checksum is None


@pytest.mark.asyncio
async def test_update_entity_without_relations(
        entity_sync_service: EntitySyncService, test_markdown: EntityMarkdown
):
    """Test first pass update."""
    # First create entity
    entity = await entity_sync_service.create_entity_from_markdown("test.md", test_markdown)

    # Modify markdown content
    test_markdown.frontmatter.title = "Updated Title"
    test_markdown.content.content = "Updated description"
    test_markdown.content.observations = [MarkdownObservation(content="Updated observation")]

    # Update entity
    updated = await entity_sync_service.update_entity_and_observations(
        entity.file_path, test_markdown
    )

    # Check fields updated
    assert updated.title == "Updated Title"
    assert updated.summary == "Updated description"
    assert len(updated.observations) == 1
    assert updated.observations[0].content == "Updated observation"

    # Check checksum cleared
    assert updated.checksum is None


@pytest.mark.asyncio
async def test_update_entity_relations(
        entity_sync_service: EntitySyncService, test_markdown: EntityMarkdown
):
    """Test second pass relation updates."""

    # add a forward link to the markdown (entity does not exist)
    test_markdown.content.relations.append(MarkdownRelation(type="depends_on", target="concept/doesnt-exist"))
        
    # Create main entity first
    entity = await entity_sync_service.create_entity_from_markdown("test.md", test_markdown)

    # Create target entities that relations point to
    other_entity = EntityModel(
        title="Other Entity",
        entity_type="test",
        permalink="concept/other-entity",
        file_path="concept/other_entity.md",
        content_type="text/markdown",
    )
    another_entity = EntityModel(
        title="Another Entity",
        entity_type="test",
        permalink="concept/another-entity",
        file_path="concept/another_entity.md",
        content_type="text/markdown",
    )
    await entity_sync_service.entity_repository.add(other_entity)
    await entity_sync_service.entity_repository.add(another_entity)

    # Update relations and set checksum
    updated = await entity_sync_service.update_entity_relations("test.md", test_markdown)

    # Check relations
    assert updated is not None, "Entity should be updated"
    assert len(updated.relations) == 3

    # Check relation details
    relations = sorted(updated.relations, key=lambda r: r.id)

    assert relations[0].relation_type == "depends_on"
    assert relations[0].from_id == entity.id
    assert relations[0].to_id == other_entity.id

    assert relations[1].relation_type == "related_to"
    assert relations[1].from_id == entity.id
    assert relations[1].to_id == another_entity.id

    assert relations[2].relation_type == "depends_on"
    assert relations[2].from_id == entity.id
    assert relations[2].to_id is None
    assert relations[2].to_name == "concept/doesnt-exist"


@pytest.mark.asyncio
async def test_two_pass_sync_flow(
        entity_sync_service: EntitySyncService, test_markdown: EntityMarkdown
):
    """Test complete two-pass sync flow."""
    # Create target entities first
    other_entity = EntityModel(
        title="Other Entity",
        entity_type="test",
        permalink="concept/other-entity",
        file_path="concept/other_entity.md",
        content_type="text/markdown",
    )
    another_entity = EntityModel(
        title="Another Entity",
        entity_type="test",
        permalink="concept/another-entity",
        file_path="concept/another_entity.md",
        content_type="text/markdown",
    )
    await entity_sync_service.entity_repository.add(other_entity)
    await entity_sync_service.entity_repository.add(another_entity)

    # First pass - create without relations
    entity = await entity_sync_service.create_entity_from_markdown("test.md", test_markdown)
    assert len(entity.relations) == 0
    assert entity.checksum is None

    # Second pass - add relations
    updated = await entity_sync_service.update_entity_relations("test.md", test_markdown)

    # Verify final state
    assert len(updated.relations) == 2

    relations = sorted(updated.relations, key=lambda r: r.relation_type)
    assert relations[0].to_id == other_entity.id
    assert relations[1].to_id == another_entity.id
