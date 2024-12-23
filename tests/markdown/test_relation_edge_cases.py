"""Tests for edge cases in relation parsing."""

import pytest

from basic_memory.markdown import KnowledgeParser


@pytest.mark.asyncio
async def test_relation_empty_target():
    """Test handling of empty targets."""
    # Empty brackets
    parser = KnowledgeParser()

    assert await parser.parse_relation("type [[]]") is None
    assert await parser.parse_relation("type [[ ]]") is None

    # Only spaces
    assert await parser.parse_relation("type [[   ]]") is None

    # Only white spaces
    assert await parser.parse_relation("  ") is None
