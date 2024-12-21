"""Tests for the markdown entity parser."""

import pytest

from basic_memory.markdown.parser import EntityParser, ParseError


def test_parse_observation_basic():
    """Test basic observation parsing with category and tags."""
    parser = EntityParser()

    obs = parser._parse_observation("- [design] Core feature #important #mvp")

    assert obs is not None
    assert obs.category == "design"
    assert obs.content == "Core feature"
    assert set(obs.tags) == {"important", "mvp"}
    assert obs.context is None


def test_parse_observation_with_context():
    """Test observation parsing with context in parentheses."""
    parser = EntityParser()

    obs = parser._parse_observation(
        "- [feature] Authentication system #security #auth (Required for MVP)"
    )
    assert obs is not None
    assert obs.category == "feature"
    assert obs.content == "Authentication system"
    assert set(obs.tags) == {"security", "auth"}
    assert obs.context == "Required for MVP"


def test_parse_observation_edge_cases():
    """Test observation parsing edge cases."""
    parser = EntityParser()

    # Multiple word tags
    obs = parser._parse_observation("- [tech] Database #high-priority #needs-review")

    assert obs is not None

    assert set(obs.tags) == {"high-priority", "needs-review"}

    # Multiple word category
    obs = parser._parse_observation("- [user experience] Design #ux")
    assert obs is not None
    assert obs.category == "user experience"

    # Parentheses in content shouldn't be treated as context
    obs = parser._parse_observation("- [code] Function (x) returns y #function")
    assert obs is not None
    assert obs.content == "Function (x) returns y"
    assert obs.context is None

    # Multiple hashtags together
    obs = parser._parse_observation("- [test] Feature #important#urgent#now")
    assert obs is not None
    assert set(obs.tags) == {"important", "urgent", "now"}


def test_parse_observation_errors():
    """Test error handling in observation parsing."""
    parser = EntityParser()

    # Missing category brackets
    with pytest.raises(ParseError, match="missing category"):
        parser._parse_observation("- Design without brackets #test")

    # Unclosed category
    with pytest.raises(ParseError, match="unclosed category"):
        parser._parse_observation("- [design Core feature #test")
