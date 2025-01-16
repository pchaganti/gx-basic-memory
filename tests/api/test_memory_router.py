"""Tests for memory router endpoints."""

import pytest

from basic_memory.schemas.memory import GraphContext


@pytest.mark.asyncio
async def test_get_memory_context(client, test_graph):
    """Test getting context from memory URL."""
    response = await client.get("/memory/test/root")
    assert response.status_code == 200

    context = GraphContext(**response.json())
    assert len(context.primary_entities) == 1
    assert context.primary_entities[0].permalink == "test/root"
    assert len(context.related_entities) > 0

    # Verify metadata
    assert context.metadata["uri"] == "memory://default/test/root"
    assert context.metadata["depth"] == 1  # default depth
    #assert context.metadata["timeframe"] == "7d"  # default timeframe
    assert isinstance(context.metadata["generated_at"], str)
    assert context.metadata["matched_entities"] == 1


@pytest.mark.asyncio
async def test_get_memory_context_pattern(client, test_graph):
    """Test getting context with pattern matching."""
    response = await client.get("/memory/test/*")
    assert response.status_code == 200

    context = GraphContext(**response.json())
    assert len(context.primary_entities) > 1  # Should match multiple test/* paths
    assert all("test/" in e.permalink for e in context.primary_entities)


@pytest.mark.asyncio
async def test_get_memory_context_depth(client, test_graph):
    """Test depth parameter affects relation traversal."""
    # With depth=1, should only get immediate connections
    response = await client.get("/memory/test/root?depth=1")
    assert response.status_code == 200
    context1 = GraphContext(**response.json())

    # With depth=2, should get deeper connections
    response = await client.get("/memory/test/root?depth=2")
    assert response.status_code == 200
    context2 = GraphContext(**response.json())

    assert len(context2.related_entities) > len(context1.related_entities)


@pytest.mark.asyncio
async def test_get_memory_context_timeframe(client, test_graph):
    """Test timeframe parameter filters by date."""
    # Recent timeframe
    response = await client.get("/memory/test/root?timeframe=1d")
    assert response.status_code == 200
    recent = GraphContext(**response.json())

    # Longer timeframe
    response = await client.get("/memory/test/root?timeframe=30d")
    assert response.status_code == 200
    older = GraphContext(**response.json())

    assert len(older.related_entities) >= len(recent.related_entities)


@pytest.mark.asyncio
async def test_get_related_context(client, test_graph):
    """Test getting related content."""
    response = await client.get("/memory/related/test/root")
    assert response.status_code == 200

    context = GraphContext(**response.json())
    assert len(context.primary_entities) > 0
    assert any("connected1" in e.permalink for e in context.related_entities)
    assert any("connected2" in e.permalink for e in context.related_entities)

@pytest.mark.asyncio
async def test_get_related_context_filters(client, test_graph):
    """Test filtering related content by relation type."""
    response = await client.get("/memory/related/test/root?relation_types=connects_to")
    assert response.status_code == 200

    context = GraphContext(**response.json())
    for relation in context.related_entities:
        if relation.type == "relation":
            assert relation.relation_type == "connects_to"




@pytest.mark.asyncio
async def test_not_found(client):
    """Test handling of non-existent paths."""
    response = await client.get("/memory/test/does-not-exist")
    assert response.status_code == 200

    context = GraphContext(**response.json())
    assert len(context.primary_entities) == 0
    assert len(context.related_entities) == 0
