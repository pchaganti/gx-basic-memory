"""Tests for content parsing."""

from textwrap import dedent

import pytest

from basic_memory.markdown.exceptions import ParseError
from basic_memory.markdown.content_parser import ContentParser

def test_parse_content_basic():
    """Test parsing basic content."""
    text = dedent("""
        # Test Entity

        Basic description.

        ## Observations
        - [test] First observation #tag (context)
        - [test] Second observation #tag1 #tag2 (more context)

        ## Relations
        - implements [[Other Entity]] (implementation)
        - uses [[Another Entity]] (usage details)
    """)

    parser = ContentParser()
    result = parser.parse(text)

    assert result.title == "Test Entity"
    assert result.description == "Basic description."
    assert len(result.observations) == 2
    assert len(result.relations) == 2
    assert result.observations[0].category == "test"
    assert result.relations[0].type == "implements"

def test_parse_content_minimal():
    """Test parsing minimal content with just title."""
    text = dedent("""
        # Test Entity
    """)

    parser = ContentParser()
    result = parser.parse(text)

    assert result.title == "Test Entity"
    assert not result.description
    assert not result.observations
    assert not result.relations

def test_parse_content_malformed():
    """Test handling malformed content items."""
    text = dedent("""
        # Test Entity

        ## Observations
        - not a valid observation
        - [test] valid observation #tag
        
        ## Relations
        - not a valid relation
        - implements [[Valid Entity]]
    """)

    parser = ContentParser()
    result = parser.parse(text)

    assert len(result.observations) == 1  # Only valid observation
    assert len(result.relations) == 1  # Only valid relation

def test_parse_content_no_title():
    """Test error when content has no title."""
    text = dedent("""
        Some content without a title.

        ## Observations
        - [test] observation
    """)

    parser = ContentParser()
    result = parser.parse(text)

    assert not result.title
    assert len(result.observations) == 1

def test_parse_content_multiline_description():
    """Test parsing multiline description."""
    text = dedent("""
        # Test Entity

        First line of description.
        Second line of description.
        Third line with more details.

        ## Observations
        - [test] observation
    """)

    parser = ContentParser()
    result = parser.parse(text)

    assert "First line" in result.description
    assert "Second line" in result.description
    assert "Third line" in result.description