"""Tests for file utilities."""

from pathlib import Path

import pytest

from basic_memory.utils.file_utils import (
    compute_checksum,
    ensure_directory,
    write_file_atomic,
    add_frontmatter,
    parse_frontmatter,
    has_frontmatter,
    remove_frontmatter,
    parse_content_with_frontmatter,
    FileError,
    FileWriteError,
    ParseError,
)


@pytest.mark.asyncio
async def test_compute_checksum():
    """Test checksum computation."""
    content = "test content"
    checksum = await compute_checksum(content)
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA-256 produces 64 char hex string


@pytest.mark.asyncio
async def test_compute_checksum_error():
    """Test checksum error handling."""
    with pytest.raises(FileError):
        # Try to hash an object that can't be encoded
        await compute_checksum(object())  # pyright: ignore [reportArgumentType]


@pytest.mark.asyncio
async def test_ensure_directory(tmp_path: Path):
    """Test directory creation."""
    test_dir = tmp_path / "test_dir"
    await ensure_directory(test_dir)
    assert test_dir.exists()
    assert test_dir.is_dir()


@pytest.mark.asyncio
async def test_write_file_atomic(tmp_path: Path):
    """Test atomic file writing."""
    test_file = tmp_path / "test.txt"
    content = "test content"

    await write_file_atomic(test_file, content)
    assert test_file.exists()
    assert test_file.read_text() == content

    # Temp file should be cleaned up
    assert not test_file.with_suffix(".tmp").exists()


@pytest.mark.asyncio
async def test_write_file_atomic_error(tmp_path: Path):
    """Test atomic write error handling."""
    # Try to write to a directory that doesn't exist
    test_file = tmp_path / "nonexistent" / "test.txt"

    with pytest.raises(FileWriteError):
        await write_file_atomic(test_file, "test content")


@pytest.mark.asyncio
async def test_add_frontmatter():
    """Test adding frontmatter."""
    content = "test content"
    metadata = {"title": "Test", "tags": ["a", "b"]}

    result = await add_frontmatter(content, metadata)

    # Should have frontmatter delimiters
    assert result.startswith("---\n")
    assert "---\n\n" in result

    # Should include metadata
    assert "title: Test" in result
    assert "- a\n- b" in result or "['a', 'b']" in result

    # Should preserve content
    assert result.endswith(f"test content")


def test_has_frontmatter():
    """Test frontmatter detection."""
    # Valid frontmatter
    assert has_frontmatter("""---
title: Test
---
content""")

    # Just content
    assert not has_frontmatter("Just content")

    # Empty content
    assert not has_frontmatter("")

    # Just delimiter
    assert not has_frontmatter("---")

    # Delimiter not at start
    assert not has_frontmatter("""
Some text
---
title: Test
---""")

    # Invalid format
    assert not has_frontmatter("--title: test--")


def test_parse_frontmatter():
    """Test parsing frontmatter."""
    # Valid frontmatter
    content = """---
title: Test
tags:
  - a
  - b
---
content"""
    
    result = parse_frontmatter(content)
    assert result == {"title": "Test", "tags": ["a", "b"]}

    # Empty frontmatter
    content = """---
---
content"""
    result = parse_frontmatter(content)
    assert result == None or result == {}

    # Invalid YAML
    with pytest.raises(ParseError):
        parse_frontmatter("""---
[invalid yaml]
---
content""")

    # No frontmatter
    with pytest.raises(ParseError):
        parse_frontmatter("Just content")

    # Incomplete frontmatter
    with pytest.raises(ParseError):
        parse_frontmatter("""---
title: Test
content""")


def test_remove_frontmatter():
    """Test removing frontmatter."""
    # With frontmatter
    content = """---
title: Test
---
test content"""
    assert remove_frontmatter(content) == "test content"

    # No frontmatter
    content = "test content"
    assert remove_frontmatter(content) == "test content"

    # Only frontmatter
    content = """---
title: Test
---
"""
    assert remove_frontmatter(content) == ""

    # frontmatter missing some fields
    assert remove_frontmatter("""---
title: Test
content""") == "---\ntitle: Test\ncontent"


@pytest.mark.asyncio
async def test_parse_content_with_frontmatter():
    """Test combined frontmatter and content parsing."""
    # Full document
    content = """---
title: Test
tags:
  - a
  - b
---
test content"""

    frontmatter, body = await parse_content_with_frontmatter(content)
    assert frontmatter == {"title": "Test", "tags": ["a", "b"]}
    assert body == "test content"

    # No frontmatter
    content = "test content"
    frontmatter, body = await parse_content_with_frontmatter(content)
    assert frontmatter == {}
    assert body == "test content"

    # Empty document
    frontmatter, body = await parse_content_with_frontmatter("")
    assert frontmatter == {}
    assert body == ""

    # Only frontmatter
    content = """---
title: Test
---
"""
    frontmatter, body = await parse_content_with_frontmatter(content)
    assert frontmatter == {"title": "Test"}
    assert body == ""


@pytest.mark.asyncio
async def test_frontmatter_whitespace_handling():
    """Test frontmatter handling with various whitespace."""
    # Extra newlines before frontmatter
    content = """

---
title: Test
---
content"""
    assert has_frontmatter(content.strip())
    frontmatter = parse_frontmatter(content.strip())
    assert frontmatter == {"title": "Test"}

    # Extra newlines after frontmatter
    content = """---
title: Test
---


content"""
    result = await add_frontmatter("content", {"title": "Test"})
    assert result.count("\n\n") == 1  # Should normalize to single blank line

    # Spaces around content
    content = """---
title: Test
---
   content   """
    assert remove_frontmatter(content).strip() == "content"