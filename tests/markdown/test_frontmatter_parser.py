"""Tests for frontmatter parsing."""
import pytest
from datetime import datetime, timezone
from textwrap import dedent

from basic_memory.utils.file_utils import parse_frontmatter, ParseError
from basic_memory.markdown.schemas.entity import EntityFrontmatter


@pytest.mark.asyncio
async def test_parse_frontmatter():
    """Test parsing valid frontmatter."""
    content = dedent("""
        ---
        type: test
        id: test/123
        created: 2024-12-22T10:00:00Z
        modified: 2024-12-22T10:00:00Z
        tags: [test, example]
        ---

        # Content
        """).strip()

    frontmatter, remaining = await parse_frontmatter(content)
    assert frontmatter["type"] == "test"
    assert frontmatter["id"] == "test/123"
    assert frontmatter["tags"] == ["test", "example"]
    assert remaining.strip() == "# Content"


@pytest.mark.asyncio
async def test_parse_frontmatter_comma_tags():
    """Test parsing tags with commas."""
    content = dedent("""
        ---
        type: test
        id: test/tags
        created: 2024-12-22T10:00:00Z
        modified: 2024-12-22T10:00:00Z
        tags: [tag1, tag2, tag3]
        ---
        """).strip()

    frontmatter, _ = await parse_frontmatter(content)
    assert frontmatter["tags"] == ["tag1", "tag2", "tag3"]


@pytest.mark.asyncio
async def test_parse_frontmatter_missing_required():
    """Test error on missing required fields."""
    content = dedent("""
        ---
        type: test
        # missing id
        created: 2024-12-22T10:00:00Z
        modified: 2024-12-22T10:00:00Z
        tags: []
        ---
        """).strip()

    with pytest.raises(ParseError):
        await parse_frontmatter(content)


@pytest.mark.asyncio
async def test_parse_frontmatter_invalid_date():
    """Test error on invalid date format."""
    content = dedent("""
        ---
        type: test
        id: test/invalid
        created: not-a-date
        modified: 2024-12-22T10:00:00Z
        tags: []
        ---
        """).strip()

    with pytest.raises(ParseError):
        await parse_frontmatter(content)


@pytest.mark.asyncio
async def test_parse_frontmatter_whitespace():
    """Test handling of extra whitespace."""
    content = dedent("""
        ---
        type:    test   
        id:   test/spaces   
        created:    2024-12-22T10:00:00Z    
        modified:    2024-12-22T10:00:00Z    
        tags:    [tag1,    tag2]   
        ---
        """).strip()

    frontmatter, _ = await parse_frontmatter(content)
    assert frontmatter["type"] == "test"
    assert frontmatter["id"] == "test/spaces"
    assert frontmatter["tags"] == ["tag1", "tag2"]