"""Tests for markdown parser edge cases."""

from pathlib import Path
from textwrap import dedent

import pytest

from basic_memory.markdown.parser import EntityParser
from basic_memory.utils.file_utils import FileError, ParseError


@pytest.mark.asyncio
async def test_unicode_content(tmp_path):
    """Test handling of Unicode content including emoji and non-Latin scripts."""
    content = dedent("""
        ---
        type: test
        id: test/unicode
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [unicode, 测试]
        ---

        # Unicode Test 🧪

        ## Observations
        - [test] Emoji test 👍 #emoji #test (Testing emoji)
        - [中文] Chinese text 测试 #language (Script test)
        - [русский] Russian привет #language (More scripts)
        - [note] Emoji in text 😀 #meta (Category test)

        ## Relations
        - tested_by [[测试组件]] (Unicode test)
        - depends_on [[компонент]] (Another test)

        ## Metadata
        ```yml
        category: test
        status: active
        ```
        """)

    test_file = tmp_path / "unicode.md"
    test_file.write_text(content, encoding="utf-8")

    parser = EntityParser()
    entity = await parser.parse_file(test_file)

    assert "测试" in entity.frontmatter.tags
    assert "китайский" not in entity.frontmatter.tags
    assert entity.content.title == "Unicode Test 🧪"


@pytest.mark.asyncio
async def test_fallback_encoding(tmp_path):
    """Test UTF-16 fallback when UTF-8 fails."""
    content = dedent("""
        Hello 世界
        No proper sections here
        """)
    test_file = tmp_path / "unicode_file.md"
    test_file.write_text(content, encoding="utf-16")

    parser = EntityParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)


@pytest.mark.asyncio
async def test_encoding_errors(tmp_path):
    """Test handling of encoding errors."""
    # Create a file with invalid UTF-8 bytes
    test_file = tmp_path / "invalid.md"
    with open(test_file, "wb") as f:
        f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8

    parser = EntityParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file, encoding="ascii")


@pytest.mark.asyncio
async def test_file_not_found():
    """Test handling of non-existent files."""
    parser = EntityParser()
    with pytest.raises(FileError):
        await parser.parse_file(Path("nonexistent.md"))


@pytest.mark.asyncio
async def test_nested_structures(tmp_path):
    """Test handling of nested markdown structures."""
    content = dedent("""
        ---
        type: test
        id: test/nested
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---

        # Nested Test

        ## Observations
        - [test] Main point #main (Top level)
            - [test] Subpoint #sub (Should be ignored)
                - [test] Sub-subpoint #detail (Also ignored)

        ## Relations
        - depends_on [[Sub Entity]] (Top level)
            - uses [[Another Entity]] (Should be ignored)
                - implements [[Third Entity]] (Also ignored)
        """)

    test_file = tmp_path / "nested.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = await parser.parse_file(test_file)

    assert len(entity.content.observations) == 3
    assert len(entity.content.relations) == 3
    assert entity.content.observations[0].tags == ["main"]
    assert entity.content.observations[0].context == "Top level"
    assert entity.content.relations[0].target == "Sub Entity"
    assert entity.content.relations[0].type == "depends_on"


@pytest.mark.asyncio
async def test_malformed_sections(tmp_path):
    """Test various malformed section contents."""
    content = dedent("""
        ---
        type: test
        id: test/malformed
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---

        # Malformed Test

        ## Observations
        - not a valid observation
        - [unclosed category content
        - no content]
        - [] empty category

        ## Relations
        - not a valid relation
        - missing_brackets Entity
        - implements incomplete [[
        - implements ]] backwards
        """)

    test_file = tmp_path / "malformed.md"
    test_file.write_text(content)

    parser = EntityParser()
    with pytest.raises(ParseError):
        entity = await parser.parse_file(test_file)


@pytest.mark.asyncio
async def test_missing_required_sections(tmp_path):
    """Test handling of missing required sections."""
    # Test file with only frontmatter
    content = dedent("""
        ---
        type: test
        id: test/incomplete
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---
        """)

    test_file = tmp_path / "incomplete.md"
    test_file.write_text(content)

    parser = EntityParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)
