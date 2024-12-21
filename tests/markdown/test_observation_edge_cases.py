"""Tests for edge cases in observation parsing."""

import pytest

from basic_memory.markdown import ParseError
from basic_memory.markdown.schemas.observation import Observation


def test_observation_empty_input():
    """Test handling of empty input."""
    assert Observation.from_line("") is None
    assert Observation.from_line("   ") is None
    assert Observation.from_line("\n") is None


def test_observation_unicode():
    """Test handling of Unicode content."""
    # Invalid UTF-8 sequences
    assert Observation.from_line("- [test] Bad UTF \xff") is None
    assert Observation.from_line("- [test] Bad UTF \xfe") is None

    # Control characters
    assert Observation.from_line("- [test] With \x00 null") is None
    assert Observation.from_line("- [test] With \x01 ctrl-a") is None
    assert Observation.from_line("- [test] With \x1b escape") is None
    assert Observation.from_line("- [test] With \x7f delete") is None
    assert Observation.from_line("- [test] With " + chr(0x1F) + " unit sep") is None

    # Valid UTF-8
    obs = Observation.from_line("- [测试] Unicode content #标签")
    assert obs is not None
    assert obs.category == "测试"
    assert "标签" in obs.tags


def test_observation_invalid_context():
    """Test handling of invalid context format."""
    obs = Observation.from_line("- [test] Content (unclosed")
    assert obs is not None
    assert obs.content == "Content (unclosed"
    assert obs.context is None

    obs = Observation.from_line("- [test] Content (with) extra) parens)")
    assert obs is not None
    assert obs.content == "Content"
    assert obs.context == "with) extra) parens"


def test_observation_complex_format():
    """Test parsing complex observation formats."""
    # Test multiple nested tags and spaces
    obs = Observation.from_line("- [complex test] This is #tag1#tag2 with #tag3 content")
    assert obs is not None
    assert obs.category == "complex test"
    assert set(obs.tags) == {"tag1", "tag2", "tag3"}
    assert obs.content == "This is with content"


def test_observation_exception_handling():
    """Test general error handling in observation parsing."""
    # Test with a problematic regex pattern that could cause catastrophic backtracking
    long_input = "[test] " + "a" * 1000000  # Very long input
    assert Observation.from_line(long_input) is None

    # Test with invalid types
    assert Observation.from_line(None) is None  # type: ignore
    assert Observation.from_line(123) is None  # type: ignore
    assert Observation.from_line(object()) is None  # type: ignore


def test_observation_malformed_category():
    """Test handling of malformed category brackets."""
    with pytest.raises(ParseError, match="unclosed category"):
        Observation.from_line("- [test Content")

    with pytest.raises(ParseError, match="missing category"):
        Observation.from_line("- test] Content")

    assert Observation.from_line("- [] Empty category") is None


def test_observation_whitespace():
    """Test handling of whitespace."""
    # Valid whitespace cases
    obs = Observation.from_line("- [test] Content")
    assert obs is not None
    assert obs.content == "Content"

    # Test individual whitespace chars
    test_chars = {
        " ": "space",
        "\t": "tab",
        #'\n': 'newline', # newline should be end of content
        "\r": "return",
    }

    for char, name in test_chars.items():
        content = f"- [test] Content{char}with{char}{name}"
        obs = Observation.from_line(content)
        assert obs is not None
        assert obs.content == f"Content with {name}"
