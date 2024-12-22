"""Tests for entity markdown parser."""

from pathlib import Path

import pytest

from basic_memory.markdown.parser import EntityParser
from basic_memory.markdown.schemas import (
    Entity,
    EntityFrontmatter,
    EntityContent,
)
from basic_memory.utils.file_utils import ParseError, FileError


@pytest.fixture
def sample_entity_content():
    """Sample entity file content."""
    return """
---
id: 123
type: test
created: 2024-12-22T10:00:00Z
modified: 2024-12-22T10:00:00Z
tags: entity, test
---

# Test Entity

A test entity for testing purposes.

## Observations
- [tech] First technical observation #tag1 (first context)
- [design] Second design observation #tag2 (second context)

## Relations
- depends_on [[Other Entity]] (Testing the relation parsing)

---
metadata:
  checksum: abc123
  doc_id: 1
---

"""


@pytest.mark.asyncio
async def test_parse_valid_file(tmp_path: Path, sample_entity_content):
    """Test parsing valid entity file."""
    # Create test file
    test_file = tmp_path / "test.md"
    test_file.write_text(sample_entity_content)

    # Parse file
    parser = EntityParser()
    entity = await parser.parse_file(test_file)

    # Verify frontmatter
    assert isinstance(entity.frontmatter, EntityFrontmatter)
    assert entity.frontmatter.type == "test"
    assert entity.frontmatter.id == "123"

    # Verify content
    assert isinstance(entity.content, EntityContent)
    assert entity.content.title == "Test Entity"
    assert entity.content.description == "A test entity for testing purposes."

    # Verify observations
    assert len(entity.content.observations) == 2
    obs1 = entity.content.observations[0]
    assert obs1.category == "tech"
    assert obs1.content == "First technical observation"
    assert obs1.tags == ["tag1"]
    assert obs1.context == "first context"

    obs2 = entity.content.observations[1]
    assert obs2.category == "design"
    assert obs2.content == "Second design observation"
    assert obs2.tags == ["tag2"]
    assert obs2.context == "second context"

    # Verify relations
    assert len(entity.content.relations) == 1
    rel = entity.content.relations[0]
    assert rel.target == "Other Entity"
    assert rel.type == "depends_on"
    assert rel.context == "Testing the relation parsing"


@pytest.mark.asyncio
async def test_parse_missing_file():
    """Test error on missing file."""
    parser = EntityParser()
    with pytest.raises(FileError):
        await parser.parse_file(Path("nonexistent.md"))


@pytest.mark.asyncio
async def test_parse_invalid_frontmatter(tmp_path: Path):
    """Test error on invalid frontmatter."""
    test_file = tmp_path / "test.md"
    # Create invalid frontmatter by removing required field
    content = """---
type: test
# missing id field
created: 2024-12-22T10:00:00Z
modified: 2024-12-22T10:00:00Z
tags: [entity]
---

# Test Entity"""
    test_file.write_text(content)

    parser = EntityParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)


@pytest.mark.asyncio
async def test_parse_no_frontmatter(tmp_path: Path):
    """Test file with no frontmatter."""
    test_file = tmp_path / "test.md"
    content = "Just content"
    test_file.write_text(content)

    parser = EntityParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)


@pytest.mark.asyncio
async def test_parse_content_str(sample_entity_content):
    """Test parsing content string directly."""
    parser = EntityParser()
    entity = await parser.parse_content_str(sample_entity_content)

    assert isinstance(entity, Entity)
    assert entity.frontmatter.type == "test"
    assert entity.frontmatter.id == "123"
    assert entity.content.title == "Test Entity"

    # Verify observations parsed correctly
    assert len(entity.content.observations) == 2
    assert entity.content.observations[0].category == "tech"
    assert entity.content.observations[1].category == "design"

    # Verify relation parsed correctly
    assert len(entity.content.relations) == 1
    assert entity.content.relations[0].type == "depends_on"
    assert entity.content.relations[0].target == "Other Entity"
