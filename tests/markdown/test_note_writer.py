"""Tests for NoteWriter."""

from datetime import datetime, UTC

import pytest
from basic_memory.models import Entity
from basic_memory.markdown.note_writer import NoteWriter
from basic_memory.models.knowledge import EntityType


@pytest.fixture
def note_writer() -> NoteWriter:
    return NoteWriter()


@pytest.fixture
def sample_note() -> Entity:
    """Create a sample note entity for testing."""
    return Entity(
        id=1,
        name="test_note",
        entity_type=EntityType.NOTE,
        path_id="notes/test_note",
        file_path="notes/test_note.md",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 2, tzinfo=UTC)
    )


@pytest.mark.asyncio
async def test_format_frontmatter_basic(note_writer: NoteWriter, sample_note: Entity):
    """Test basic frontmatter formatting."""
    frontmatter = await note_writer.format_frontmatter(sample_note)
    
    assert frontmatter["id"] == "notes/test_note"
    assert frontmatter["type"] == EntityType.NOTE
    assert frontmatter["created"] == "2025-01-01T00:00:00+00:00"
    assert frontmatter["modified"] == "2025-01-02T00:00:00+00:00"


@pytest.mark.asyncio
async def test_format_frontmatter_with_metadata(note_writer: NoteWriter, sample_note: Entity):
    """Test frontmatter includes entity metadata."""
    sample_note.entity_metadata = {
        "category": "research",
        "tags": ["python", "testing"]
    }
    
    frontmatter = await note_writer.format_frontmatter(sample_note)
    
    assert frontmatter["category"] == "research"
    assert frontmatter["tags"] == ["python", "testing"]
    assert frontmatter["id"] == "notes/test_note"


@pytest.mark.asyncio
async def test_format_content_basic(note_writer: NoteWriter, sample_note: Entity):
    """Test basic content formatting."""
    content = "# Test Note\n\nThis is a test note."
    result = await note_writer.format_content(sample_note, content)
    
    assert result == content


@pytest.mark.asyncio
async def test_format_content_strips_whitespace(note_writer: NoteWriter, sample_note: Entity):
    """Test content formatting strips extra whitespace."""
    content = "\n\n# Test Note\n\nThis is a test note.\n\n"
    result = await note_writer.format_content(sample_note, content)
    
    assert result == "# Test Note\n\nThis is a test note."


@pytest.mark.asyncio
async def test_format_content_preserves_markdown(note_writer: NoteWriter, sample_note: Entity):
    """Test content formatting preserves markdown formatting."""
    content = """# Test Note

This note has:
- Bullet points
- *Italic text*
- **Bold text**
- `code blocks`

```python
def test():
    pass
```"""
    
    result = await note_writer.format_content(sample_note, content)
    assert result == content