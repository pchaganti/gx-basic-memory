"""Tests for edge cases in relation parsing."""

import pytest

from basic_memory.markdown import ParseError, EntityParser


@pytest.mark.asyncio
async def test_relation_empty_target():
    """Test handling of empty targets."""
    # Empty brackets
    parser = EntityParser()

    assert await parser.parse_relation("type [[]]") is None
    assert await parser.parse_relation("type [[ ]]") is None

    # Only spaces
    assert await parser.parse_relation("type [[   ]]") is None

    # Only white spaces
    assert await parser.parse_relation("  ") is None


@pytest.mark.asyncio
async def test_relation_malformed_context():
    """Test handling of malformed context formats."""
    parser = EntityParser()

    # Missing parentheses
    with pytest.raises(ParseError, match="invalid context format"):
        await parser.parse_relation("type [[Target]] context without parens")

    # Unclosed parentheses
    with pytest.raises(ParseError, match="invalid context format"):
        await parser.parse_relation("type [[Target]] (unclosed")

    # Extra closing parentheses
    with pytest.raises(ParseError, match="invalid context format"):
        await parser.parse_relation("type [[Target]] (closed twice))")


@pytest.mark.asyncio
async def test_relation_generic_errors():
    """Test general error handling in relation parsing."""
    parser = EntityParser()

    # Invalid input that should trigger exception handling
    assert await parser.parse_relation(None) is None  # type: ignore
    assert await parser.parse_relation(123) is None  # type: ignore
    assert await parser.parse_relation(object()) is None  # type: ignore
