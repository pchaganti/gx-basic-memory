"""Tests for edge cases in entity parsing."""

from datetime import datetime
from textwrap import dedent

import pytest

from basic_memory.markdown import ParseError
from basic_memory.markdown.schemas.entity import (
    Entity,
    EntityFrontmatter,
    EntityContent,
)


def test_entity_content_empty_lists():
    """Test entity content with empty lists."""
    content = dedent("""
        # Empty Entity

        ## Observations

        ## Relations
    """)

    entity_content = EntityContent.from_markdown(content)
    assert entity_content.observations == []
    assert entity_content.relations == []


def test_entity_content_multiline_description():
    """Test entity content with a multiline description."""
    content = dedent("""
        # Title
        First line
        Second line
        Third line

        ## Observations
        - [test] Test
    """)

    entity = EntityContent.from_markdown(content)
    assert entity.title == "Title"
    # Each line should be as-is
    assert entity.description == "First line\nSecond line\nThird line"


def test_entity_content_invalid_tokens():
    """Test entity content with invalid markdown tokens."""
    entity = EntityContent.from_markdown("# Title\n## Section\n```invalid\n")
    assert entity.title == "Title"
    assert not entity.observations
    assert not entity.relations


def test_frontmatter_parsing_errors():
    """Test error handling in frontmatter parsing."""
    # Test various invalid formats
    with pytest.raises(ParseError):
        EntityFrontmatter.from_text("not yaml")

    with pytest.raises(ParseError):
        EntityFrontmatter.from_text("missing:fields")

    with pytest.raises(ParseError):
        EntityFrontmatter.from_text("type:test\nid:test\ncreated:invalid")


def test_content_parsing_errors():
    """Test error handling in content parsing."""
    # Test various markdown edge cases
    with pytest.raises(ParseError):
        EntityContent.from_markdown(None)  # type: ignore

    with pytest.raises(ParseError):
        EntityContent.from_markdown(object())  # type: ignore

    content = dedent("""
        # Title
        ## Invalid
        - [not a section] content
    """)

    entity = EntityContent.from_markdown(content)
    assert entity.title == "Title"
    assert not entity.observations


def test_invalid_entity_creation():
    """Test error handling in full entity creation."""
    # Invalid frontmatter
    frontmatter = EntityFrontmatter(
        type="test", id="test", created=datetime.now(), modified=datetime.now(), tags=[]
    )

    # Invalid content
    content = EntityContent(title="", description=None, observations=[], relations=[])

    # Should still create valid entity
    entity = Entity(frontmatter=frontmatter, content=content)
    assert entity.frontmatter.type == "test"
    assert entity.content.title == ""
