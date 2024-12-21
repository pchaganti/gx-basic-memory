"""Tests for metadata parsing."""

from textwrap import dedent

from basic_memory.markdown import EntityMetadata


def test_parse_metadata():
    """Test parsing basic metadata."""
    text = dedent("""
        owner: team-auth
        priority: high
        status: active
    """)

    result = EntityMetadata.from_text(text)

    assert result.metadata["owner"] == "team-auth"
    assert result.metadata["priority"] == "high"
    assert result.metadata["status"] == "active"


def test_parse_metadata_empty():
    """Test parsing empty metadata."""
    text = ""

    result = EntityMetadata.from_text(text)
    assert result.metadata == {}


def test_parse_metadata_whitespace():
    """Test handling of various whitespace in metadata."""
    text = dedent("""
        owner:     team-auth    
        priority:      high     
        status:   active     
    """)

    result = EntityMetadata.from_text(text)

    assert result.metadata["owner"] == "team-auth"
    assert result.metadata["priority"] == "high"
    assert result.metadata["status"] == "active"


def test_parse_metadata_multiline_values():
    """Test handling of multiline metadata values."""
    text = dedent("""
        owner: team-auth
        description: This is a
         multiline value
         with several lines
        status: active
    """)

    result = EntityMetadata.from_text(text)

    assert result.metadata["owner"] == "team-auth"
    assert result.metadata["status"] == "active"
    assert len(result.metadata["description"].splitlines()) == 3


def test_parse_metadata_invalid():
    """Test handling of invalid metadata format."""
    text = dedent("""
        owner team-auth
        priority: high
    """)

    result = EntityMetadata.from_text(text)

    assert "priority" in result.metadata
    assert "owner" not in result.metadata
