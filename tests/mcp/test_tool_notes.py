"""Tests for note tools that exercise the full stack with SQLite."""

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from basic_memory.mcp.tools import notes


@pytest.mark.asyncio
async def test_write_note(app):
    """Test creating a new note.
    
    Should:
    - Create entity with correct type and content
    - Save markdown content
    - Handle tags correctly
    - Return valid permalink
    """
    permalink = await notes.write_note(
        file_path="Test Note",
        content="# Test\nThis is a test note",
        tags=["test", "documentation"]
    )
    
    assert permalink  # Got a valid permalink
    
    # Try reading it back
    content = await notes.read_note(permalink)
    assert "# Test\nThis is a test note" in content
    assert "tags:" in content
    assert "- '#test'" in content
    assert "- '#documentation'" in content


@pytest.mark.asyncio
async def test_write_note_no_tags(app):
    """Test creating a note without tags."""
    permalink = await notes.write_note(
        file_path="Simple Note",
        content="Just some text"
    )
    
    # Should be able to read it back
    content = await notes.read_note(permalink)
    assert "Just some text" in content
    assert "tags:" not in content


@pytest.mark.asyncio
async def test_read_note_not_found(app):
    """Test trying to read a non-existent note."""
    with pytest.raises(ToolError, match="Error calling tool: Client error '404 Not Found'"):
        await notes.read_note("notes/does-not-exist")


@pytest.mark.asyncio
async def test_write_note_update_existing(app):
    """Test creating a new note.

    Should:
    - Create entity with correct type and content
    - Save markdown content
    - Handle tags correctly
    - Return valid permalink
    """
    permalink = await notes.write_note(
        file_path="Test Note",
        content="# Test\nThis is a test note",
        tags=["test", "documentation"]
    )

    assert permalink  # Got a valid permalink

    permalink = await notes.write_note(
        file_path="Test Note",
        content="# Test\nThis is an updated note",
        tags=["test", "documentation"]
    )


    # Try reading it back
    content = await notes.read_note(permalink)
    assert "# Test\nThis is an updated note" in content
    assert "tags:" in content
    assert "- '#test'" in content
    assert "- '#documentation'" in content


@pytest.mark.asyncio
async def test_read_note_by_title(app):
    """Test reading a note by its title."""
    # First create a note
    await notes.write_note(
        file_path="Special Note",
        content="Note content here"
    )
    
    # Should be able to read it by title
    content = await notes.read_note("Special Note")
    assert "Note content here" in content




@pytest.mark.asyncio
async def test_note_unicode_content(app):
    """Test handling of unicode content in notes."""
    content = "# Test 🚀\nThis note has emoji 🎉 and unicode ♠♣♥♦"
    permalink = await notes.write_note(
        file_path="Unicode Test",
        content=content
    )
    
    # Read back should preserve unicode
    result = await notes.read_note(permalink)
    assert content in result


@pytest.mark.asyncio
async def test_multiple_notes(app):
    """Test creating and managing multiple notes."""
    # Create several notes
    notes_data = [
        ("Note 1", "Content 1", ["tag1"]),
        ("Note 2", "Content 2", ["tag1", "tag2"]),
        ("Note 3", "Content 3", []),
    ]
    
    permalinks = []
    for file_path, content, tags in notes_data:
        permalink = await notes.write_note(file_path=file_path, content=content, tags=tags)
        permalinks.append(permalink)
        
    # Should be able to read each one
    for i, permalink in enumerate(permalinks):
        content = await notes.read_note(permalink)
        assert f"Content {i+1}" in content


@pytest.mark.asyncio
async def test_delete_note_existing(app):
    """Test deleting a new note.

    Should:
    - Create entity with correct type and content
    - Return valid permalink
    - Delete the note
    """
    permalink = await notes.write_note(
        file_path="Test Note",
        content="# Test\nThis is a test note",
        tags=["test", "documentation"]
    )

    assert permalink  # Got a valid permalink

    deleted = await notes.delete_note(permalink)
    assert deleted is True

@pytest.mark.asyncio
async def test_delete_note_doesnt_exist(app):
    """Test deleting a new note.

    Should:
    - Delete the note
    - verify returns false
    """
    deleted = await notes.delete_note("doesnt-exist")
    assert deleted is False
