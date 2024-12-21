"""Tests for edge cases in relation parsing."""

import pytest

from basic_memory.markdown import ParseError
from basic_memory.markdown.schemas.relation import Relation


def test_relation_empty_target():
    """Test handling of empty targets."""
    # Empty brackets
    assert Relation.from_line("type [[]]") is None
    assert Relation.from_line("type [[ ]]") is None

    # Only spaces
    assert Relation.from_line("type [[   ]]") is None

    # Only white spaces
    assert Relation.from_line("  ") is None


def test_relation_malformed_context():
    """Test handling of malformed context formats."""
    # Missing parentheses
    with pytest.raises(ParseError, match="invalid context format"):
        Relation.from_line("type [[Target]] context without parens")

    # Unclosed parentheses
    with pytest.raises(ParseError, match="invalid context format"):
        Relation.from_line("type [[Target]] (unclosed")

    # Extra closing parentheses
    with pytest.raises(ParseError, match="invalid context format"):
        Relation.from_line("type [[Target]] (closed twice))")


def test_relation_generic_errors():
    """Test general error handling in relation parsing."""
    # Invalid input that should trigger exception handling
    assert Relation.from_line(None) is None  # type: ignore
    assert Relation.from_line(123) is None  # type: ignore
    assert Relation.from_line(object()) is None  # type: ignore
