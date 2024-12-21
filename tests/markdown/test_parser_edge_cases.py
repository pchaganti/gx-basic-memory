"""Tests for markdown parser edge cases."""

from pathlib import Path
import pytest
from textwrap import dedent

from basic_memory.markdown.parser import EntityParser, ParseError


def test_unicode_content(tmp_path):
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
        - [test] Emoji test 👍 #emoji #test
        - [中文] Chinese text 测试 #language
        - [русский] Russian привет #language
        - [😀] Emoji category #meta (Category test)

        ## Relations
        - implements [[测试组件]] (Unicode test)
        - used_by [[компонент]] (Another test)

        ---
        category: test
        status: active
        ---
        """)

    test_file = tmp_path / "unicode.md"
    test_file.write_text(content, encoding="utf-8")

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    assert "测试" in entity.frontmatter.tags
    assert "китайский" not in entity.frontmatter.tags
    assert entity.content.title == "Unicode Test 🧪"


def test_fallback_encoding(tmp_path):
    """Test UTF-16 fallback when UTF-8 fails."""
    content = "Hello 世界"  # Simple content that works in both encodings
    test_file = tmp_path / "unicode_file.md"
    test_file.write_text(content, encoding="utf-16")

    parser = EntityParser()
    with pytest.raises(ParseError, match="Missing required document sections"):
        parser.parse_file(test_file)


def test_encoding_errors(tmp_path):
    """Test handling of encoding errors."""
    # Create a file with invalid UTF-8 bytes
    test_file = tmp_path / "invalid.md"
    with open(test_file, "wb") as f:
        f.write(b"\xFF\xFE\x00\x00")  # Invalid UTF-8

    parser = EntityParser()
    with pytest.raises(ParseError, match="Failed to parse"):
        parser.parse_file(test_file, encoding="ascii")


def test_file_not_found():
    """Test handling of non-existent files."""
    parser = EntityParser()
    with pytest.raises(ParseError, match="File does not exist"):
        parser.parse_file(Path("nonexistent.md"))


def test_nested_structures(tmp_path):
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
        - [test] Main point #main
            - [sub] Subpoint #sub
                - [subsub] Sub-subpoint #detail

        ## Relations
        - contains [[Sub Entity]]
            - and [[Another Entity]]
                - also [[Third Entity]]
        """)

    test_file = tmp_path / "nested.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    # Only top-level items should be parsed
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1


def test_malformed_sections(tmp_path):
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
        - missing type [[Entity]]
        - incomplete [[
        - ]] backwards
        """)

    test_file = tmp_path / "malformed.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    # Should skip invalid entries but not fail completely
    assert len(entity.content.observations) == 0
    assert len(entity.content.relations) == 0


def test_missing_required_sections(tmp_path):
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
    with pytest.raises(ParseError, match="Missing required document sections"):
        parser.parse_file(test_file)