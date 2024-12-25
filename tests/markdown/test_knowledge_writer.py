"""Tests for knowledge entity writer."""
from datetime import datetime, UTC

import pytest

from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import (
    Entity as EntityModel,
    Observation,
    Relation, ObservationCategory,
)


@pytest.fixture
def writer():
    """Create writer instance."""
    return KnowledgeWriter()


@pytest.fixture
def test_entity():
    """Create test entity with observations and relations."""
    now = datetime.now(UTC)
    # Create main entity
    entity = EntityModel(
        id=1,
        path_id="test/test_entity",
        name="TestEntity",
        entity_type="test",
        description="A test entity",
        created_at=now,
        updated_at=now
    )

    # Add observations with categories and context
    entity.observations = [
        Observation(
            content="Technical implementation detail",
            category=ObservationCategory.TECH.value,
            context="Initial implementation"
        ),
        Observation(
            content="Design pattern choice",
            category=ObservationCategory.DESIGN.value
        ),
    ]

    # Create related entity
    other_entity = EntityModel(
        id=2,
        path_id="test/other_entity",
        name="OtherEntity",
        entity_type="test",
        created_at=now,
        updated_at=now
    )

    # Create relation from main entity to other
    relation = Relation(from_entity=entity, to_entity=other_entity, relation_type="relates_to")
    entity.from_relations = [relation]

    return entity


@pytest.mark.asyncio
async def test_format_frontmatter(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test frontmatter generation."""
    frontmatter = await writer.format_frontmatter(test_entity)

    assert frontmatter["type"] == "test"
    assert frontmatter["id"] == "test/test_entity"
    assert isinstance(frontmatter["created"], str)
    assert isinstance(frontmatter["modified"], str)


@pytest.mark.asyncio
async def test_format_content_with_categories(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test content formatting with categorized observations."""
    content = await writer.format_content(test_entity)

    # Check observations section header and format comment
    assert "## Observations" in content
    assert "<!-- Format: - [category] Content text #tag1 #tag2 (optional context) -->" in content

    # Check formatted observations
    assert "- [tech] Technical implementation detail (Initial implementation)" in content
    assert "- [design] Design pattern choice" in content


@pytest.mark.asyncio
async def test_format_content_default_category(writer: KnowledgeWriter):
    """Test formatting observation with default category."""
    entity = EntityModel(id=1, name="Test", entity_type="test")
    entity.observations = [
        Observation(content="Simple note", category=ObservationCategory.NOTE.value) 
    ]

    content = await writer.format_content(entity)
    assert "- [note] Simple note" in content


@pytest.mark.asyncio
async def test_format_content_context_handling(writer: KnowledgeWriter):
    """Test formatting observations with different context scenarios."""
    entity = EntityModel(id=1, name="Test", entity_type="test")
    entity.observations = [
        # With context
        Observation(
            content="With context",
            category=ObservationCategory.TECH.value,
            context="Important context"
        ),
        # Without context
        Observation(
            content="No context",
            category=ObservationCategory.TECH.value
        ),
    ]

    content = await writer.format_content(entity)
    assert "- [tech] With context (Important context)" in content
    assert "- [tech] No context" in content
    assert "No context ()" not in content  # Shouldn't have empty parentheses


@pytest.mark.asyncio
async def test_format_content_sections_order(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test proper order and spacing of sections with new format."""
    content = await writer.format_content(test_entity)
    lines = content.split("\n")

    # Find key sections
    title_idx = next(i for i, line in enumerate(lines) if line.startswith("# "))
    obs_idx = next(i for i, line in enumerate(lines) if line.strip() == "## Observations")
    format_idx = next(i for i, line in enumerate(lines) if "<!-- Format:" in line)
    first_obs_idx = next(i for i, line in enumerate(lines) if line.startswith("- ["))

    # Verify order and spacing
    assert obs_idx > title_idx  # Observations after title
    assert format_idx == obs_idx + 1  # Format comment right after header
    assert lines[format_idx + 1] == ""  # Blank line after format comment
    assert first_obs_idx == format_idx + 2  # First observation after blank line


@pytest.mark.asyncio
async def test_format_content_with_metadata(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test content formatting with metadata section."""
    metadata = {"ai_generated": True, "confidence": 0.95, "tags": ["test", "example"]}

    content = await writer.format_content(test_entity, metadata)

    # Regular content should be there
    assert "# TestEntity" in content
    assert "## Observations" in content

    # Metadata section should be properly formatted
    assert "# Metadata" in content
    assert "<!-- anything below this line is for AI -->" in content
    assert "```yml" in content
    assert "ai_generated: true" in content.lower()
    assert "confidence: 0.95" in content
    assert "tags:" in content
    assert "- test" in content
    assert "- example" in content


@pytest.mark.asyncio
async def test_format_metadata_only(writer: KnowledgeWriter):
    """Test metadata formatting alone."""
    metadata = {"test": "value", "nested": {"key": "value"}}

    content = await writer.format_metadata(metadata)

    assert content.startswith("# Metadata\n")
    assert "<!-- anything below this line is for AI -->" in content
    assert "```yml" in content
    assert "test: value" in content
    assert "nested:" in content
    assert "  key: value" in content
    assert content.strip().endswith("```")


@pytest.mark.asyncio
async def test_format_metadata_empty(writer: KnowledgeWriter):
    """Test metadata formatting with empty/none metadata."""
    assert await writer.format_metadata(None) == ""
    assert await writer.format_metadata({}) == ""


@pytest.mark.asyncio
async def test_format_content_minimal_entity(writer: KnowledgeWriter):
    """Test formatting with minimal entity."""
    entity = EntityModel(id=1, name="Minimal", entity_type="test")

    content = await writer.format_content(entity)

    # Should have title only
    assert content.strip() == "# Minimal"

