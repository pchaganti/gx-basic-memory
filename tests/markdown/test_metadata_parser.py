"""Tests for metadata parsing."""

from textwrap import dedent

import pytest

from basic_memory.utils.file_utils import parse_frontmatter


@pytest.mark.asyncio
async def test_parse_metadata():
    """Test parsing basic metadata."""
    text = dedent("""
        owner: team-auth
        priority: high
        status: active
    """)

    result, remaining = await parse_frontmatter(text)

    assert result["owner"] == "team-auth"
    assert result["priority"] == "high"
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_parse_metadata_empty():
    """Test parsing empty metadata."""
    text = ""

    result, remaining = await parse_frontmatter(text)
    assert result == {}


@pytest.mark.asyncio
async def test_parse_metadata_whitespace():
    """Test handling of various whitespace in metadata."""
    text = dedent("""
        owner:     team-auth    
        priority:      high     
        status:   active     
    """)

    result, remaining = await parse_frontmatter(text)

    assert result["owner"] == "team-auth"
    assert result["priority"] == "high"
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_parse_metadata_multiline_values():
    """Test handling of multiline metadata values."""
    text = dedent("""
        owner: team-auth
        description: This is a
         multiline value
         with several lines
        status: active
    """)

    result, _ = await parse_frontmatter(text)

    assert result["owner"] == "team-auth"
    assert result["status"] == "active"
    assert len(result["description"].splitlines()) == 3


@pytest.mark.asyncio
async def test_parse_metadata_invalid():
    """Test handling of invalid metadata format."""
    text = dedent("""
        owner team-auth
        priority: high
    """)

    result, _ = await parse_frontmatter(text)

    assert "priority" in result
    assert "owner" not in result
