"""Tests for KnowledgeWriter."""

from datetime import datetime, UTC

import pytest

from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Entity, Observation, Relation


@pytest.fixture
def knowledge_writer() -> KnowledgeWriter:
    return KnowledgeWriter()


@pytest.fixture
def sample_entity() -> Entity:
    """Create a sample knowledge entity for testing."""
    return Entity(
        id=1,
        title="test_entity",
        entity_type="test",
        permalink="knowledge/test_entity",
        file_path="knowledge/test_entity.md",
        summary="Test description",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 2, tzinfo=UTC),
    )


@pytest.fixture
def entity_with_observations(sample_entity: Entity) -> Entity:
    """Create an entity with observations."""
    sample_entity.observations = [
        Observation(entity_id=1, category="tech", content="First observation"),
        Observation(
            entity_id=1, category="design", content="Second observation", context="Some context"
        ),
    ]
    return sample_entity


@pytest.fixture
def entity_with_relations(sample_entity: Entity) -> Entity:
    """Create an entity with relations."""
    target = Entity(
        id=2, title="target_entity", entity_type="test", permalink="knowledge/target_entity"
    )
    sample_entity.outgoing_relations = [
        Relation(from_id=1, to_id=2, relation_type="connects_to", to_entity=target)
    ]
    return sample_entity


@pytest.mark.asyncio
async def test_format_frontmatter_basic(knowledge_writer: KnowledgeWriter, sample_entity: Entity):
    """Test basic frontmatter formatting."""
    frontmatter = await knowledge_writer.format_frontmatter(sample_entity)

    assert frontmatter["id"] == "knowledge/test_entity"
    assert frontmatter["type"] == "test"
    assert frontmatter["created"] == "2025-01-01T00:00:00+00:00"
    assert frontmatter["modified"] == "2025-01-02T00:00:00+00:00"


@pytest.mark.asyncio
async def test_format_frontmatter_with_metadata(
    knowledge_writer: KnowledgeWriter, sample_entity: Entity
):
    """Test frontmatter includes entity metadata."""
    sample_entity.entity_metadata = {"status": "active", "priority": "high"}

    frontmatter = await knowledge_writer.format_frontmatter(sample_entity)

    assert frontmatter["status"] == "active"
    assert frontmatter["priority"] == "high"
    assert frontmatter["id"] == "knowledge/test_entity"


@pytest.mark.asyncio
async def test_format_content_raw(knowledge_writer: KnowledgeWriter, sample_entity: Entity):
    """Test raw content is preserved."""
    raw_content = "# Test Content\n\nThis is some test content."
    result = await knowledge_writer.format_content(sample_entity, raw_content)

    assert result == raw_content
    assert "# test_entity" not in result  # Shouldn't add title


@pytest.mark.asyncio
async def test_format_content_basic(knowledge_writer: KnowledgeWriter, sample_entity: Entity):
    """Test basic content formatting without raw content."""
    result = await knowledge_writer.format_content(sample_entity)

    assert "# test_entity" in result
    assert "Test description" in result


@pytest.mark.asyncio
async def test_format_content_structured(
    knowledge_writer: KnowledgeWriter, entity_with_observations: Entity
):
    """Test structured content generation."""
    result = await knowledge_writer.format_content(entity_with_observations)

    # Should only have observation sections, not duplicate title
    assert "## Observations" in result
    assert "- [tech] First observation" in result
    assert "- [design] Second observation (Some context)" in result
    assert "# test_entity" not in result  # No title needed


@pytest.mark.asyncio
async def test_format_content_with_relations(
    knowledge_writer: KnowledgeWriter, entity_with_relations: Entity
):
    """Test content formatting with relations."""
    result = await knowledge_writer.format_content(entity_with_relations)

    assert "## Relations" in result
    assert "- connects_to [[target_entity]]" in result


@pytest.mark.asyncio
async def test_format_content_empty_returns_title(
    knowledge_writer: KnowledgeWriter, sample_entity: Entity
):
    """Test that empty content falls back to title."""
    sample_entity.summary = None  # Remove summary
    result = await knowledge_writer.format_content(sample_entity)

    assert result == "# test_entity"


@pytest.mark.asyncio
async def test_format_content_preserves_spacing(
    knowledge_writer: KnowledgeWriter, entity_with_observations: Entity
):
    """Test proper markdown spacing is maintained."""
    result = await knowledge_writer.format_content(entity_with_observations)
    lines = result.split("\n")

    # Find sections and verify their format structure
    for i, line in enumerate(lines):
        if line == "## Observations":
            # Observations section should have format:
            # ## Observations
            # <!-- Format comment -->
            # <empty line>
            # - observation entries...
            assert "<!--" in lines[i + 1], "Missing format comment after Observations"
            assert lines[i + 2] == "", "Missing empty line after format comment"
            assert lines[i + 3].startswith("- "), "Should start observations after empty line"

        elif line == "## Relations":
            # Relations section should have format:
            # ## Relations
            # <!-- Format comment -->
            # <empty line>
            # - relation entries...
            assert "<!--" in lines[i + 1], "Missing format comment after Relations"
            assert lines[i + 2] == "", "Missing empty line after format comment"
            if i + 3 < len(lines):  # If there are relations
                assert lines[i + 3].startswith("- "), "Should start relations after empty line"


@pytest.mark.asyncio
async def test_format_content_mixed(
    knowledge_writer: KnowledgeWriter,
    entity_with_relations: Entity,
    entity_with_observations: Entity,
):
    """Test content with both raw content and structured data."""
    # Add observations to entity with relations
    entity_with_relations.observations = entity_with_observations.observations

    # Test with raw content
    raw_content = "# Custom Title\n\nSome content."
    result = await knowledge_writer.format_content(entity_with_relations, raw_content)

    # Should preserve raw content
    assert result == raw_content
    assert "# test_entity" not in result

    # Test without raw content - should generate structured
    result = await knowledge_writer.format_content(entity_with_relations)

    assert "## Observations" in result
    assert "## Relations" in result
    assert "- [tech] First observation" in result
    assert "- connects_to [[target_entity]]" in result


@pytest.mark.asyncio
async def test_format_content_preserves_tags(
    knowledge_writer: KnowledgeWriter, sample_entity: Entity
):
    """Test that observation tags are preserved in formatting."""
    sample_entity.observations = [
        Observation(
            entity_id=1, category="tech", content="First observation", tags=["important", "bug"]
        ),
        Observation(
            entity_id=1,
            category="design",
            content="Second observation",
            tags=["feature"],
            context="Some context",
        ),
        Observation(entity_id=1, category="note", content="Third observation without tags"),
    ]

    result = await knowledge_writer.format_content(sample_entity)

    # Check that tags are formatted correctly
    assert (
        "- [tech] First observation #important #bug" in result
        or "- [tech] First observation #bug #important" in result
    )
    assert "- [design] Second observation #feature (Some context)" in result
    assert "- [note] Third observation without tags" in result

    # Verify formatting with multiple elements
    lines = result.split("\n")
    obs_section = False
    for line in lines:
        if line == "## Observations":
            obs_section = True
            continue
        if obs_section and line.startswith("- "):
            if "First observation" in line:
                # Tags should be space-separated and sorted
                assert " #bug #important" in line
            if "Second observation" in line:
                # Tags should appear before context
                assert "#feature (Some context)" in line
