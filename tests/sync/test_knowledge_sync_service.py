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
from basic_memory.sync.knowledge_sync_service import KnowledgeSyncService


@pytest_asyncio.fixture
def test_frontmatter() -> EntityFrontmatter:
    """Create test frontmatter."""
    return EntityFrontmatter(
        title="Test Entity",
        type="knowledge",
        id="concept/test_entity",
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
            MarkdownRelation(type="depends_on", target="concept/other_entity"),
            MarkdownRelation(type="related_to", target="concept/another_entity"),
        ],
    )


@pytest_asyncio.fixture
def test_markdown(test_frontmatter, test_content) -> EntityMarkdown:
    """Create complete test markdown entity."""
    return EntityMarkdown(
        frontmatter=test_frontmatter, content=test_content
    )


@pytest.mark.asyncio
async def test_create_entity_without_relations(
    knowledge_sync_service: KnowledgeSyncService, test_markdown: EntityMarkdown
):
    """Test first pass creation without relations."""
    # Create entity first pass
    entity = await knowledge_sync_service.create_entity_and_observations("test.md", test_markdown)

    # Check basic fields
    assert entity.name == "Test Entity"
    assert entity.entity_type == "knowledge"
    assert entity.path_id == "concept/test_entity"
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
    knowledge_sync_service: KnowledgeSyncService, test_markdown: EntityMarkdown
):
    """Test first pass update."""
    # First create entity
    entity = await knowledge_sync_service.create_entity_and_observations("test.md", test_markdown)

    # Modify markdown content
    test_markdown.frontmatter.title = "Updated Title"
    test_markdown.content.content = "Updated description"
    test_markdown.content.observations = [MarkdownObservation(content="Updated observation")]

    # Update entity
    updated = await knowledge_sync_service.update_entity_and_observations(
        entity.path_id, test_markdown
    )

    # Check fields updated
    assert updated.name == "Updated Title"
    assert updated.summary == "Updated description"
    assert len(updated.observations) == 1
    assert updated.observations[0].content == "Updated observation"

    # Check checksum cleared
    assert updated.checksum is None


@pytest.mark.asyncio
async def test_update_entity_relations(
    knowledge_sync_service: KnowledgeSyncService, test_markdown: EntityMarkdown
):
    """Test second pass relation updates."""
    # Create main entity first
    entity = await knowledge_sync_service.create_entity_and_observations("test.md", test_markdown)

    # Create target entities that relations point to
    other_entity = EntityModel(
        name="Other Entity",
        entity_type="test",
        path_id="concept/other_entity",
        file_path="concept/other_entity.md",
        content_type="text/markdown",
    )
    another_entity = EntityModel(
        name="Another Entity",
        entity_type="test",
        path_id="concept/another_entity",
        file_path="concept/another_entity.md",
        content_type="text/markdown",
    )
    await knowledge_sync_service.entity_service.add(other_entity)
    await knowledge_sync_service.entity_service.add(another_entity)

    # Update relations and set checksum
    test_checksum = "test-checksum-123"
    updated = await knowledge_sync_service.update_entity_relations(test_markdown, test_checksum)

    # Check relations
    assert len(updated.relations) == 2

    # Check relation details
    relations = sorted(updated.relations, key=lambda r: r.relation_type)

    assert relations[0].relation_type == "depends_on"
    assert relations[0].from_path_id == entity.id
    assert relations[0].to_path_id == other_entity.id

    assert relations[1].relation_type == "related_to"
    assert relations[1].from_path_id == entity.id
    assert relations[1].to_path_id == another_entity.id

    # Check checksum set
    assert updated.checksum == test_checksum


@pytest.mark.asyncio
async def test_two_pass_sync_flow(
    knowledge_sync_service: KnowledgeSyncService, test_markdown: EntityMarkdown
):
    """Test complete two-pass sync flow."""
    # Create target entities first
    other_entity = EntityModel(
        name="Other Entity",
        entity_type="test",
        path_id="concept/other_entity",
        file_path="concept/other_entity.md",
        content_type="text/markdown",
    )
    another_entity = EntityModel(
        name="Another Entity",
        entity_type="test",
        path_id="concept/another_entity",
        file_path="concept/another_entity.md",
        content_type="text/markdown",
    )
    await knowledge_sync_service.entity_service.add(other_entity)
    await knowledge_sync_service.entity_service.add(another_entity)

    # First pass - create without relations
    entity = await knowledge_sync_service.create_entity_and_observations("test.md", test_markdown)
    assert len(entity.relations) == 0
    assert entity.checksum is None

    # Second pass - add relations
    checksum = "final-checksum-456"
    updated = await knowledge_sync_service.update_entity_relations(test_markdown, checksum)

    # Verify final state
    assert len(updated.relations) == 2
    assert updated.checksum == checksum

    relations = sorted(updated.relations, key=lambda r: r.relation_type)
    assert relations[0].to_path_id == other_entity.id
    assert relations[1].to_path_id == another_entity.id
