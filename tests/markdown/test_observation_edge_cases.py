"""Tests for observation parsing edge cases."""

import pytest
from pathlib import Path

from basic_memory.markdown.parser import EntityParser, ParseError
from basic_memory.markdown.schemas.observation import Observation


def test_observation_empty_input():
    """Test handling of empty input."""
    assert Observation.from_line("") is None
    assert Observation.from_line("   ") is None
    assert Observation.from_line("\n") is None


def test_observation_malformed_input():
    """Test handling of malformed input."""
    assert Observation.from_line("- [] Empty category") is None
    assert Observation.from_line("- [ ] Space in brackets") is None
    assert Observation.from_line("- [  ] Multiple spaces") is None


def test_observation_invalid_context():
    """Test handling of invalid context format."""
    obs = Observation.from_line("- [test] Content (unclosed")
    assert obs is not None
    assert obs.content == "Content (unclosed"
    assert obs.context is None

    obs = Observation.from_line("- [test] Content (with) extra) parens)")
    assert obs is not None
    assert obs.content == "Content"
    assert obs.context == "with) extra"

    # Test nested parentheses
    obs = Observation.from_line("- [test] Function (result = f(x)) (implementation note)")
    assert obs is not None
    assert obs.content == "Function (result = f(x))"
    assert obs.context == "implementation note"


def test_observation_complex_format():
    """Test parsing complex observation formats."""
    # Test multiple nested tags and spaces
    obs = Observation.from_line("- [complex test] This is #tag1#tag2 with #tag3 content")
    assert obs is not None
    assert obs.category == "complex test"
    assert set(obs.tags) == {"tag1", "tag2", "tag3"}
    assert obs.content == "This is with content"

    # Test Unicode tags
    obs = Observation.from_line("- [test] Content #测试 #русский")
    assert obs is not None
    assert "测试" in obs.tags
    assert "русский" in obs.tags


def test_observation_exception_handling():
    """Test general exception handling in observation parsing."""
    # Test with a problematic regex pattern that could cause catastrophic backtracking
    long_input = "[test] " + "a" * 1000000  # Very long input
    assert Observation.from_line(long_input) is None

    # Test with Unicode category
    obs = Observation.from_line("- [测试] Content #tag")
    assert obs is not None
    assert obs.category == "测试"

    # Test malformed Unicode
    malformed = "- [test] Bad UTF \xFF"
    assert Observation.from_line(malformed) is None