"""Tests for entity metadata parsing."""

from textwrap import dedent

import pytest

from basic_memory.markdown.parser import EntityParser


@pytest.mark.asyncio
async def test_parse_metadata():
    """Test parsing basic metadata."""
    parser = EntityParser()
    metadata = {
        "owner": "team-auth",
        "priority": "high",
        "status": "active"
    }

    result = await parser.parse_metadata(metadata)

    assert result.metadata["owner"] == "team-auth"
    assert result.metadata["priority"] == "high"
    assert result.metadata["status"] == "active"


@pytest.mark.asyncio
async def test_parse_metadata_empty():
    """Test parsing empty metadata."""
    parser = EntityParser()
    result = await parser.parse_metadata(None)
    assert result.metadata == {}

    # Should also handle empty dict
    result = await parser.parse_metadata({})
    assert result.metadata == {}


@pytest.mark.asyncio
async def test_parse_metadata_whitespace():
    """Test handling of various whitespace in metadata."""
    parser = EntityParser()
    metadata = {
        "owner": "   team-auth    ",
        "priority": "    high     ",
        "status": "   active     "
    }

    result = await parser.parse_metadata(metadata)

    assert result.metadata["owner"] == "   team-auth    "  # Metadata preserves whitespace
    assert result.metadata["priority"] == "    high     "
    assert result.metadata["status"] == "   active     "


@pytest.mark.asyncio
async def test_parse_metadata_nested_objects():
    """Test handling of nested metadata objects."""
    parser = EntityParser()
    metadata = {
        "owner": "team-auth",
        "config": {
            "level": "high",
            "tags": ["important", "urgent"],
            "settings": {
                "notifications": True,
                "visibility": "private"
            }
        }
    }

    result = await parser.parse_metadata(metadata)

    assert result.metadata["owner"] == "team-auth"
    assert result.metadata["config"]["level"] == "high"
    assert result.metadata["config"]["tags"] == ["important", "urgent"]
    assert result.metadata["config"]["settings"]["notifications"] is True
    assert result.metadata["config"]["settings"]["visibility"] == "private"


@pytest.mark.asyncio
async def test_parse_metadata_mixed_types():
    """Test handling of different value types in metadata."""
    parser = EntityParser()
    metadata = {
        "owner": "team-auth",
        "active": True,
        "priority": 1,
        "tags": ["tag1", "tag2"],
        "scores": {
            "a": 10,
            "b": 20
        }
    }

    result = await parser.parse_metadata(metadata)

    assert result.metadata["owner"] == "team-auth"
    assert result.metadata["active"] is True
    assert result.metadata["priority"] == 1
    assert result.metadata["tags"] == ["tag1", "tag2"]
    assert result.metadata["scores"]["a"] == 10
    assert result.metadata["scores"]["b"] == 20