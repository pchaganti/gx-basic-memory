"""Tests for knowledge entity writer."""

import pytest

from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Entity as EntityModel, Observation, Relation


@pytest.fixture
def writer():
    """Create writer instance."""
    return KnowledgeWriter()


@pytest.fixture
def test_entity():
    """Create test entity with observations and relations."""
    # Create main entity
    entity = EntityModel(id=123, name="TestEntity", entity_type="test", description="A test entity")

    # Add observations
    entity.observations = [
        Observation(content="First observation"),
        Observation(content="Second observation"),
    ]

    # Create related entity
    other_entity = EntityModel(id=456, name="OtherEntity", entity_type="test")

    # Create relation from main entity to other
    relation = Relation(from_entity=entity, to_entity=other_entity, relation_type="relates_to")
    entity.from_relations = [relation]

    return entity


@pytest.mark.asyncio
async def test_format_frontmatter(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test frontmatter generation."""
    frontmatter = await writer.format_frontmatter(test_entity)

    assert frontmatter["type"] == "test"
    assert frontmatter["id"] == 123
    assert isinstance(frontmatter["created"], str)
    assert isinstance(frontmatter["modified"], str)


@pytest.mark.asyncio
async def test_format_content_basic(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test basic content formatting without metadata."""
    content = await writer.format_content(test_entity)

    # Check sections
    assert content.startswith("# TestEntity\n")
    assert "A test entity" in content
    assert "## Observations" in content
    assert "- First observation" in content
    assert "- Second observation" in content
    assert "## Relations" in content
    assert "- [[OtherEntity]] relates_to" in content

    # Should not have metadata section
    assert "# Metadata" not in content
    assert "```yml" not in content


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


@pytest.mark.asyncio
async def test_content_section_spacing(writer: KnowledgeWriter, test_entity: EntityModel):
    """Test proper spacing between sections."""
    content = await writer.format_content(test_entity)
    lines = content.split("\n")

    # Find section headers
    section_indexes = [i for i, line in enumerate(lines) if line.startswith("##")]

    for idx in section_indexes:
        # Should be blank line before header
        assert lines[idx - 1] == "", f"No blank line before section at line {idx}"
        # Content should start right after header
        assert lines[idx + 1].strip(), f"No content after section at line {idx}"
