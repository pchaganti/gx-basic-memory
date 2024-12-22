"""Tests for the markdown entity parser."""

import pytest

from basic_memory.markdown.parser import EntityParser, ParseError


@pytest.mark.asyncio
async def test_parse_observation_basic():
    """Test basic observation parsing with category and tags."""
    parser = EntityParser()

    obs = await parser.parse_observation("- [design] Core feature #important #mvp")

    assert obs is not None
    assert obs.category == "design"
    assert obs.content == "Core feature"
    assert set(obs.tags) == {"important", "mvp"}  # pyright: ignore [reportArgumentType]
    assert obs.context is None


@pytest.mark.asyncio
async def test_parse_observation_with_context():
    """Test observation parsing with context in parentheses."""
    parser = EntityParser()

    obs = await parser.parse_observation(
        "- [feature] Authentication system #security #auth (Required for MVP)"
    )
    assert obs is not None
    assert obs.category == "feature"
    assert obs.content == "Authentication system"
    assert set(obs.tags) == {"security", "auth"}  # pyright: ignore [reportArgumentType]
    assert obs.context == "Required for MVP"


@pytest.mark.asyncio
async def test_parse_observation_edge_cases():
    """Test observation parsing edge cases."""
    parser = EntityParser()

    # Multiple word tags
    obs = await parser.parse_observation("- [tech] Database #high-priority #needs-review")

    assert obs is not None

    assert set(obs.tags) == {"high-priority", "needs-review"}  # pyright: ignore [reportArgumentType]

    # Multiple word category
    obs = await parser.parse_observation("- [user experience] Design #ux")
    assert obs is not None
    assert obs.category == "user experience"

    # Parentheses in content shouldn't be treated as context
    obs = await parser.parse_observation("- [code] Function (x) returns y #function")
    assert obs is not None
    assert obs.content == "Function (x) returns y"
    assert obs.context is None

    # Multiple hashtags together
    obs = await parser.parse_observation("- [test] Feature #important#urgent#now")
    assert obs is not None
    assert set(obs.tags) == {"important", "urgent", "now"}  # pyright: ignore [reportArgumentType]


@pytest.mark.asyncio
async def test_parse_observation_errors():
    """Test error handling in observation parsing."""
    parser = EntityParser()

    # Missing category brackets
    with pytest.raises(ParseError, match="missing category"):
        await parser.parse_observation("- Design without brackets #test")

    # Unclosed category
    with pytest.raises(ParseError, match="unclosed category"):
        await parser.parse_observation("- [design Core feature #test")
