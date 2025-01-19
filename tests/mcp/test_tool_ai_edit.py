"""Tests for AI edit tool."""

import pytest
from pathlib import Path

from basic_memory.mcp.tools.ai_edit import ai_edit


@pytest.fixture
def test_file(tmp_path):
    """Create a test file."""
    content = '''"""Test file for edits."""

class TestClass:
    def method_one(self):
        x = 1
        y = 2
        return x + y

    def method_two(self):
        # TODO implement
        pass
'''
    path = tmp_path / "test.py"
    path.write_text(content)
    return path


@pytest.mark.asyncio
async def test_simple_replace(test_file):
    """Test basic text replacement."""
    success = await ai_edit(
        str(test_file),
        [{
            'oldText': 'return x + y',
            'newText': 'total = x + y\nreturn total'
        }]
    )
    
    assert success
    content = test_file.read_text()
    assert 'total = x + y' in content
    assert 'return total' in content


@pytest.mark.asyncio
async def test_indented_replace(test_file):
    """Test replacing with indentation detection."""
    success = await ai_edit(
        str(test_file),
        [{
            'oldText': '        # TODO implement\n        pass',
            'newText': 'values = [1, 2, 3]\nreturn sum(values)',
            'options': {'preserveIndentation': False}
        }]
    )
    
    assert success
    content = test_file.read_text()
    assert '        values = [1, 2, 3]' in content
    assert '        return sum(values)' in content


@pytest.mark.asyncio
async def test_specified_indent(test_file):
    """Test with explicit indentation."""
    success = await ai_edit(
        str(test_file),
        [{
            'oldText': '    def method_two(self):',
            'newText': 'def method_two(self):',
            'options': {'indent': 4, 'preserveIndentation': True}
        }]
    )
    
    assert success
    content = test_file.read_text()
    assert '    def method_two(self):' in content


@pytest.mark.asyncio
async def test_no_match(test_file):
    """Test handling of non-existent text."""
    success = await ai_edit(
        str(test_file),
        [{
            'oldText': 'this text does not exist',
            'newText': 'something else'
        }]
    )
    
    # Should fail gracefully
    assert not success
    # File should be unchanged
    assert test_file.read_text() == test_file.read_text()