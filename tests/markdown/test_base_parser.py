"""Tests for base markdown parser."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List

import pytest

from basic_memory.markdown.base_parser import MarkdownParser, ParseError, FileError


@dataclass
class TestDoc:
    """Simple document for testing."""
    title: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class TestParser(MarkdownParser[TestDoc]):
    """Concrete parser implementation for testing."""

    async def parse_frontmatter(self, frontmatter: Dict[str, Any]) -> str:
        """Extract title from frontmatter."""
        if "title" not in frontmatter:
            raise ParseError("Missing required title")
        return frontmatter["title"]

    async def parse_content(self, title: str, sections: Dict[str, str]) -> str:
        """Process sections into content string."""
        if "content" in sections:
            return sections["content"]
        # Join all section content if no direct content section
        return "\n".join(sections.values())

    async def parse_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Pass through metadata."""
        return metadata

    async def create_document(
        self,
        frontmatter: str,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> TestDoc:
        """Create test document."""
        return TestDoc(title=frontmatter, content=content, metadata=metadata)


@pytest.mark.asyncio
async def test_parse_valid_file(tmp_path: Path):
    """Test parsing valid file."""
    # Create test file
    test_file = tmp_path / "test.md"
    content = """---
title: Test Doc
metadata:
  key: value
---

# Title
Test content
"""
    test_file.write_text(content)

    # Parse file
    parser = TestParser()
    doc = await parser.parse_file(test_file)

    assert doc.title == "Test Doc"
    assert doc.content == "Test content"
    assert doc.metadata == {"key": "value"}


@pytest.mark.asyncio
async def test_parse_missing_file():
    """Test error on missing file."""
    parser = TestParser()
    with pytest.raises(FileError):
        await parser.parse_file(Path("nonexistent.md"))


@pytest.mark.asyncio
async def test_parse_invalid_frontmatter(tmp_path: Path):
    """Test error on invalid frontmatter."""
    test_file = tmp_path / "test.md"
    content = """---
not_title: Test Doc
---

# Title
content"""
    test_file.write_text(content)

    parser = TestParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)


@pytest.mark.asyncio
async def test_parse_no_frontmatter(tmp_path: Path):
    """Test file with no frontmatter."""
    test_file = tmp_path / "test.md"
    content = """# Title
Just content"""
    test_file.write_text(content)

    parser = TestParser()
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)


@pytest.mark.asyncio
async def test_parse_content_str():
    """Test parsing content string directly."""
    content = """---
title: Test Doc
---

# Title
Test content"""

    parser = TestParser()
    doc = await parser.parse_content_str(content)

    assert doc.title == "Test Doc"
    assert doc.content == "Test content"
    assert doc.metadata is None