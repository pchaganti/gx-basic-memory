"""Tests for entity frontmatter parsing."""

from datetime import datetime

import pytest

from basic_memory.markdown.knowledge_parser import KnowledgeParser, ParseError


@pytest.mark.asyncio
async def test_parse_frontmatter():
    """Test parsing valid frontmatter."""
    parser = KnowledgeParser()
    frontmatter_dict = {
        "type": "test",
        "id": "test/123",
        "created": "2024-12-22T10:00:00Z",
        "modified": "2024-12-22T10:00:00Z",
        "tags": ["test", "example"],
    }

    result = await parser.parse_frontmatter(frontmatter_dict)
    assert result.type == "test"
    assert result.id == "test/123"
    assert result.tags == ["test", "example"]
    assert isinstance(result.created, datetime)
    assert isinstance(result.modified, datetime)


@pytest.mark.asyncio
async def test_parse_frontmatter_comma_tags():
    """Test parsing tags with commas."""
    parser = KnowledgeParser()
    frontmatter_dict = {
        "type": "test",
        "id": "test/tags",
        "created": "2024-12-22T10:00:00Z",
        "modified": "2024-12-22T10:00:00Z",
        "tags": "tag1, tag2, tag3",  # String format
    }

    result = await parser.parse_frontmatter(frontmatter_dict)
    assert result.tags == ["tag1", "tag2", "tag3"]


@pytest.mark.asyncio
async def test_parse_frontmatter_missing_required():
    """Test error on missing required fields."""
    parser = KnowledgeParser()
    frontmatter_dict = {
        "type": "test",
        # missing id
        "created": "2024-12-22T10:00:00Z",
        "modified": "2024-12-22T10:00:00Z",
        "tags": [],
    }

    with pytest.raises(ParseError, match="Missing required frontmatter fields: id"):
        await parser.parse_frontmatter(frontmatter_dict)


@pytest.mark.asyncio
async def test_parse_frontmatter_invalid_date():
    """Test error on invalid date format."""
    parser = KnowledgeParser()
    frontmatter_dict = {
        "type": "test",
        "id": "test/invalid",
        "created": "not-a-date",
        "modified": "2024-12-22T10:00:00Z",
        "tags": [],
    }

    with pytest.raises(ParseError, match="Invalid date format for created"):
        await parser.parse_frontmatter(frontmatter_dict)


@pytest.mark.asyncio
async def test_parse_frontmatter_whitespace():
    """Test handling of extra whitespace."""
    parser = KnowledgeParser()
    frontmatter_dict = {
        "type": "   test   ",
        "id": "   test/spaces   ",
        "created": "2024-12-22T10:00:00Z",
        "modified": "2024-12-22T10:00:00Z",
        "tags": "   tag1   ,    tag2   ",
    }

    result = await parser.parse_frontmatter(frontmatter_dict)
    assert result.type == "test"  # Pydantic should strip whitespace
    assert result.id == "test/spaces"
    assert result.tags == ["tag1", "tag2"]


@pytest.mark.asyncio
async def test_parse_frontmatter_empty_tags():
    """Test handling of empty tags field."""
    parser = KnowledgeParser()
    frontmatter_dict = {
        "type": "test",
        "id": "test/notags",
        "created": "2024-12-22T10:00:00Z",
        "modified": "2024-12-22T10:00:00Z",
        # No tags field
    }

    result = await parser.parse_frontmatter(frontmatter_dict)
    assert result.tags == []  # Should default to empty list
