"""Tests for frontmatter parsing."""

from datetime import datetime, UTC
from textwrap import dedent

import pytest

from basic_memory.markdown import EntityFrontmatter
from basic_memory.markdown.exceptions import ParseError


def test_parse_frontmatter():
    """Test parsing basic frontmatter."""
    text = dedent("""
        type: component
        id: test/basic
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: test, base
    """)

    result = EntityFrontmatter.from_text(text)

    assert result.type == "component"
    assert result.id == "test/basic"
    assert result.created == datetime(2024, 12, 21, 14, 0, tzinfo=UTC)
    assert result.modified == datetime(2024, 12, 21, 14, 0, tzinfo=UTC)
    assert result.tags == ["test", "base"]


def test_parse_frontmatter_comma_tags():
    """Test parsing frontmatter with comma-separated tags."""
    text = dedent("""
        type: component
        id: test/comma-tags
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: first, second, third
    """)

    result = EntityFrontmatter.from_text(text)

    assert result.tags == ["first", "second", "third"]


def test_parse_frontmatter_missing_required():
    """Test error on missing required fields."""
    text = dedent("""
        type: component
        # Missing id
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
    """)

    with pytest.raises(ParseError):
        EntityFrontmatter.from_text(text)


def test_parse_frontmatter_invalid_date():
    """Test error on invalid date format."""
    text = dedent("""
        type: component
        id: test/dates
        created: not-a-date
        modified: 2024-12-21T14:00:00Z
        tags: 
    """)

    with pytest.raises(ParseError):
        EntityFrontmatter.from_text(text)


def test_parse_frontmatter_whitespace():
    """Test handling of various whitespace in frontmatter."""
    text = dedent("""
        type:    component   
        id:     test/whitespace    
        created:     2024-12-21T14:00:00Z    
        modified:    2024-12-21T14:00:00Z       
        tags:     one,  two  ,   three      
    """)

    result = EntityFrontmatter.from_text(text)

    assert result.type == "component"
    assert result.id == "test/whitespace"
    assert result.tags == ["one", "two", "three"]
