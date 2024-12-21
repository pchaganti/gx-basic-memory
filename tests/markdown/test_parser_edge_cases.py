"""Tests for edge cases in markdown parsing."""

from datetime import datetime
from textwrap import dedent

import pytest

from basic_memory.markdown import (
    EntityParser,
    ParseError,
    Entity,
    EntityFrontmatter,
    EntityContent,
    EntityMetadata,
)

def test_unicode_content(tmp_path):
    """Test handling of Unicode content including emoji and non-Latin scripts."""
    content = dedent('''
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
        ''')

    test_file = tmp_path / "unicode.md"
    test_file.write_text(content, encoding='utf-8')

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    assert "测试" in entity.frontmatter.tags
    assert entity.content.title == "Unicode Test 🧪"
    assert "👍" in entity.content.observations[0].content
    assert "测试" in entity.content.observations[1].content

def test_long_content(tmp_path):
    """Test handling of very long content at our limits."""
    # Create a long observation right at our length limit
    long_obs = "x" * 995 + " #tag"  # 1000 chars with tag

    content = dedent(f'''
        ---
        type: test
        id: test/long
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [long]
        ---

        # Long Content Test

        ## Description
        {"Very long description " * 100}

        ## Observations
        - [test] {long_obs}

        ## Relations
        - related_to [[{"Very long entity name " * 10}]] (Long context test)
        ''')

    test_file = tmp_path / "long.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    # Check that long content is preserved
    assert len(entity.content.observations[0].content) == 995
    assert len(entity.content.description) > 1000

def test_missing_sections(tmp_path):
    """Test handling of files missing required sections."""
    content = dedent("""
        # No Metadata
        Just some content.
    """)

    test_file = tmp_path / "missing.md"
    test_file.write_text(content)

    parser = EntityParser()
    with pytest.raises(ParseError):
        parser.parse_file(test_file)

def test_nested_structures(tmp_path):
    """Test handling of nested markdown structures."""
    content = dedent('''
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
        ''')

    test_file = tmp_path / "nested.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    # Only top-level items should be parsed
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1

def test_mixed_newlines(tmp_path):
    """Test handling of different newline styles (\n, \r\n, \r)."""
    content = "---\\ntype: test\\r\\nid: test/newlines\\ncreated: 2024-12-21T14:00:00Z\\rmodified: 2024-12-21T14:00:00Z\\ntags: [test]\\n---\\n\\r\\n# Test\\r\\n## Observations\\n- [test] Line 1\\r- [test] Line 2\\n".replace('\\n', '\n').replace('\\r', '\r')

    test_file = tmp_path / "newlines.md"
    test_file.write_text(content, encoding='utf-8')

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    assert len(entity.content.observations) == 2

def test_malformed_sections(tmp_path):
    """Test various malformed section contents."""
    content = dedent('''
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
        ''')

    test_file = tmp_path / "malformed.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    # Should skip invalid entries but not fail completely
    assert len(entity.content.observations) == 0
    assert len(entity.content.relations) == 0