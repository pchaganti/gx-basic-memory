"""Tests for file utilities."""

from pathlib import Path

import pytest

from basic_memory.utils.file_utils import (
    compute_checksum,
    ensure_directory,
    write_file_atomic,
    add_frontmatter,
    parse_frontmatter,
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
    assert result.endswith(content)


@pytest.mark.asyncio
async def test_parse_frontmatter():
    """Test parsing frontmatter."""
    content = """---
title: Test
tags:
  - a
  - b
---

test content"""

    metadata, remaining = await parse_frontmatter(content)

    assert metadata == {"title": "Test", "tags": ["a", "b"]}
    assert remaining.strip() == "test content"


@pytest.mark.asyncio
async def test_parse_frontmatter_no_frontmatter():
    """Test parsing content without frontmatter."""
    content = "test content"
    metadata, remaining = await parse_frontmatter(content)

    assert metadata == {}
    assert remaining == content


@pytest.mark.asyncio
async def test_parse_frontmatter_error():
    """Test frontmatter parse error handling."""
    # Really invalid YAML frontmatter
    content = """---
[[ this is not valid yaml ]]
title:: [}
---

test content"""

    with pytest.raises(ParseError):
        await parse_frontmatter(content)
