"""Tests for link resolution service."""

import pytest
import pytest_asyncio

from basic_memory.models.knowledge import Entity
from basic_memory.services.link_resolver import LinkResolver


@pytest_asyncio.fixture
async def link_resolver(entity_repository):
    """Create LinkResolver instance."""
    return LinkResolver(entity_repository)


@pytest.mark.asyncio
async def test_exact_permalink_match(
    link_resolver, entity_repository
):
    """Test resolving a link that exactly matches a permalink."""
    # Create test entity
    entity = Entity(
        title="Test Entity",
        entity_type="test",
        summary="A test entity",
        permalink="specs/test-entity",
        file_path="specs/test-entity.md",
        content_type="text/markdown"
    )
    await entity_repository.add(entity)
    
    # Test exact permalink match
    result = await link_resolver.resolve_link("specs/test-entity")
    assert result == "specs/test-entity"


@pytest.mark.asyncio
async def test_normalize_link_text(link_resolver):
    """Test link text normalization."""
    assert link_resolver._normalize_link_text("[[Test Entity]]") == "Test Entity"
    assert link_resolver._normalize_link_text("Test Entity|Alias") == "Test Entity"
    assert link_resolver._normalize_link_text("  Test Entity  ") == "Test Entity"
    assert link_resolver._normalize_link_text("specs/test-entity") == "specs/test-entity"


@pytest.mark.asyncio
async def test_title_match(
    link_resolver, entity_repository
):
    """Test resolving a link that matches an entity title."""
    # Create test entity
    entity = Entity(
        title="Test Entity",
        entity_type="test",
        summary="A test entity",
        permalink="specs/test-entity",
        file_path="specs/test-entity.md",
        content_type="text/markdown"
    )
    await entity_repository.add(entity)
    
    # Test title match
    result = await link_resolver.resolve_link("Test Entity")
    assert result == "specs/test-entity"


@pytest.mark.asyncio
async def test_no_match_returns_original(link_resolver):
    """Test that unmatched links return original text."""
    result = await link_resolver.resolve_link("Non Existent Entity")
    assert result == "Non Existent Entity"


@pytest.mark.asyncio
async def test_obsidian_style_links(
    link_resolver, entity_repository
):
    """Test handling Obsidian-style links with aliases."""
    # Create test entity
    entity = Entity(
        title="Original Title",
        entity_type="test",
        summary="A test entity",
        permalink="test/original-title",
        file_path="test/original-title.md",
        content_type="text/markdown"
    )
    await entity_repository.add(entity)
    
    # Test with Obsidian link formats
    result = await link_resolver.resolve_link("[[Original Title|Display Text]]")
    assert result == "test/original-title"


@pytest.mark.asyncio
async def test_error_handling(
    link_resolver, entity_repository, monkeypatch
):
    """Test error handling during link resolution."""
    # Mock repository to raise an exception
    async def mock_get_by_permalink(*args, **kwargs):
        raise Exception("Test error")
    monkeypatch.setattr(entity_repository, "get_by_permalink", mock_get_by_permalink)
    
    # Should return original text on error
    result = await link_resolver.resolve_link("Test Entity")
    assert result == "Test Entity"