"""Tests for edge cases in relation parsing."""

import pytest

from basic_memory.markdown import EntityParser


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
