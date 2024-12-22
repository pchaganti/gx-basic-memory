"""Tests for edge cases in observation parsing."""

import pytest

from basic_memory.markdown import ParseError, EntityParser


@pytest.mark.asyncio
async def test_observation_empty_input():
    """Test handling of empty input."""
    parser = EntityParser()
    assert await parser.parse_observation("") is None
    assert await parser.parse_observation("   ") is None
    assert await parser.parse_observation("\n") is None


@pytest.mark.asyncio
async def test_observation_unicode():
    """Test handling of Unicode content."""
    # Invalid UTF-8 sequences
    parser = EntityParser()
    assert await parser.parse_observation("- [test] Bad UTF \xff") is None
    assert await parser.parse_observation("- [test] Bad UTF \xfe") is None

    # Control characters
    assert await parser.parse_observation("- [test] With \x00 null") is None
    assert await parser.parse_observation("- [test] With \x01 ctrl-a") is None
    assert await parser.parse_observation("- [test] With \x1b escape") is None
    assert await parser.parse_observation("- [test] With \x7f delete") is None
    assert await parser.parse_observation("- [test] With " + chr(0x1F) + " unit sep") is None

    # Valid UTF-8
    obs = await parser.parse_observation("- [测试] Unicode content #标签")
    assert obs is not None
    assert obs.category == "测试"
    assert "标签" in obs.tags  # pyright: ignore [reportOperatorIssue]


@pytest.mark.asyncio
async def test_observation_invalid_context():
    """Test handling of invalid context format."""
    parser = EntityParser()
    obs = await parser.parse_observation("- [test] Content (unclosed")
    assert obs is not None
    assert obs.content == "Content (unclosed"
    assert obs.context is None

    obs = await parser.parse_observation("- [test] Content (with) extra) parens)")
    assert obs is not None
    assert obs.content == "Content"
    assert obs.context == "with) extra) parens"


@pytest.mark.asyncio
async def test_observation_complex_format():
    """Test parsing complex observation formats."""
    # Test multiple nested tags and spaces
    parser = EntityParser()
    obs = await parser.parse_observation("- [complex test] This is #tag1#tag2 with #tag3 content")
    assert obs is not None
    assert obs.category == "complex test"
    assert set(obs.tags) == {"tag1", "tag2", "tag3"}  # pyright: ignore [reportArgumentType]
    assert obs.content == "This is with content"


@pytest.mark.asyncio
async def test_observation_exception_handling():
    """Test general error handling in observation parsing."""
    # Test with a problematic regex pattern that could cause catastrophic backtracking
    long_input = "[test] " + "a" * 1000000  # Very long input
    parser = EntityParser()

    assert await parser.parse_observation(long_input) is None

    # Test with invalid types
    assert await parser.parse_observation(None) is None  # type: ignore
    assert await parser.parse_observation(123) is None  # type: ignore
    assert await parser.parse_observation(object()) is None  # type: ignore


@pytest.mark.asyncio
async def test_observation_malformed_category():
    """Test handling of malformed category brackets."""

    parser = EntityParser()
    with pytest.raises(ParseError, match="unclosed category"):
        await parser.parse_observation("- [test Content")

    with pytest.raises(ParseError, match="missing category"):
        await parser.parse_observation("- test] Content")

    assert await parser.parse_observation("- [] Empty category") is None


@pytest.mark.asyncio
async def test_observation_whitespace():
    """Test handling of whitespace."""
    # Valid whitespace cases

    parser = EntityParser()
    obs = await parser.parse_observation("- [test] Content")
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
        obs = await parser.parse_observation(content)
        assert obs is not None
        assert obs.content == f"Content with {name}"
