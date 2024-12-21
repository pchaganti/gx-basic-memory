"""Tests for edge cases and tricky inputs in the markdown parser."""
from datetime import datetime
from pathlib import Path
from textwrap import dedent
import pytest

from basic_memory.markdown.parser import EntityParser, ParseError, EntityFrontmatter, EntityContent, Entity

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
    ''')
    
    test_file = tmp_path / "unicode.md"
    test_file.write_text(content, encoding='utf-8')
    
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    assert "测试" in entity.frontmatter.tags
    assert entity.content.title == "Unicode Test 🧪"
    assert "👍" in entity.content.observations[0].content
    assert entity.content.observations[2].category == "русский"
    assert entity.content.observations[3].category == "😀"
    assert entity.content.relations[0].target == "测试组件"

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
    assert entity.content.observations[0].tags == ["tag"]

def test_mixed_newlines(tmp_path):
    """Test handling of different newline styles (\\n, \\r\\n, \\r)."""
    content = "---\\ntype: test\\r\\nid: test/newlines\\ncreated: 2024-12-21T14:00:00Z\\rmodified: 2024-12-21T14:00:00Z\\ntags: [test]\\n---\\n\\r\\n# Test\\r\\n## Observations\\n- [test] Line 1\\r- [test] Line 2\\n".replace('\\n', '\n').replace('\\r', '\r')
    
    test_file = tmp_path / "newlines.md"
    test_file.write_text(content, encoding='utf-8')
    
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    assert len(entity.content.observations) == 2

def test_malformed_frontmatter(tmp_path):
    """Test various malformed frontmatter cases."""
    cases = [
        # Invalid YAML syntax
        '''---
        type: : test: :
        id: test/bad
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---''',
        
        # Invalid datetime format
        '''---
        type: test
        id: test/bad
        created: not-a-date
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---''',
        
        # Missing required field
        '''---
        type: test
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---''',
        
        # Extra fields
        '''---
        type: test
        id: test/extra
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        nonexistent_field: value
        ---'''
    ]
    
    parser = EntityParser()
    test_file = tmp_path / "bad.md"
    
    for i, case in enumerate(cases):
        content = case + "\n# Test"
        test_file.write_text(content)
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

def test_file_encodings(tmp_path):
    """Test different file encodings."""
    encodings = ['utf-8', 'utf-16', 'latin1']
    content = dedent('''
        ---
        type: test
        id: test/encoding
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: [test]
        ---
        
        # Encoding Test
        
        ## Observations
        - [test] ASCII content #test
        - [utf8] UTF-8 content 测试 #unicode
    ''')
    
    parser = EntityParser()
    
    for encoding in encodings:
        test_file = tmp_path / f"encoding_{encoding}.md"
        test_file.write_text(content, encoding=encoding)
        
        try:
            entity = parser.parse_file(test_file)
            assert len(entity.content.observations) == 2
        except UnicodeError:
            # Some encodings might not handle all characters
            pass

def test_empty_sections(tmp_path):
    """Test handling of empty sections."""
    content = dedent('''
        ---
        type: test
        id: test/empty
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
        ---
        
        # Empty Test
        
        ## Description
        
        ## Observations
        
        ## Relations
        
        ## Context
        
        ## Metadata
    ''')
    
    test_file = tmp_path / "empty.md"
    test_file.write_text(content)
    
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    assert entity.content.description == ""
    assert entity.content.observations == []
    assert entity.content.relations == []
    assert entity.content.context == ""
    assert entity.content.metadata == {}

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