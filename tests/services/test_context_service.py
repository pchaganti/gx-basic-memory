"""Tests for context service."""

from datetime import datetime, timedelta, UTC

import pytest
import pytest_asyncio

from basic_memory.schemas.search import SearchItemType
from basic_memory.services.context_service import ContextService


@pytest_asyncio.fixture
async def context_service(search_repository, entity_repository):
    """Create context service for testing."""
    return ContextService(search_repository, entity_repository)


@pytest.mark.asyncio
async def test_find_by_pattern(context_service, test_graph):
    """Test pattern matching."""
    results = await context_service.find_by_permalink("test/*")
    assert len(results) > 0
    assert all("test/" in r.permalink for r in results)


@pytest.mark.asyncio
async def test_find_by_permalink(context_service, test_graph):
    """Test exact permalink lookup."""
    results = await context_service.find_by_permalink("test/root")
    assert len(results) == 1
    assert results[0].permalink == "test/root"


@pytest.mark.asyncio
async def test_find_related(context_service, test_graph):
    """Test finding related content."""
    results = await context_service.find_related_1("test/root")
    # Should get immediate connections
    assert any("connected1" in r.permalink for r in results)
    assert any("connected2" in r.permalink for r in results)


@pytest.mark.asyncio
async def test_find_connected_basic(context_service, test_graph, search_service):
    """Test basic connectivity traversal."""
    # Start with root entity and one of its observations
    type_id_pairs = [
        ("entity", test_graph["root"].id),
        ("observation", test_graph["observations"][0].id),
    ]

    results = await context_service.find_connected(type_id_pairs)

    # Verify types
    types_found = {r.type for r in results}
    assert "entity" in types_found
    assert "relation" in types_found
    assert "observation" in types_found

    # Verify we found directly connected entities
    entity_ids = {r.id for r in results if r.type == "entity"}
    assert test_graph["connected1"].id in entity_ids
    assert test_graph["connected2"].id in entity_ids

    # Verify we found observations
    assert any(r.type == "observation" and "Root note 1" in r.content for r in results)


@pytest.mark.asyncio
async def test_find_connected_depth_limit(context_service, test_graph):
    """Test depth limiting works.
    Our traversal path is:
    - Depth 0: Root
    - Depth 1: Relations + directly connected entities (Connected1, Connected2)
    - Depth 2: Relations + next level entities (Deep)
    """
    type_id_pairs = [("entity", test_graph["root"].id)]

    # With depth=1, we get direct connections
    shallow_results = await context_service.find_connected(type_id_pairs, max_depth=1)
    shallow_entities = {(r.id, r.type) for r in shallow_results if r.type == "entity"}
    # Should find Connected1 and Connected2
    assert (test_graph["connected1"].id, "entity") in shallow_entities
    assert (test_graph["connected2"].id, "entity") in shallow_entities
    # But not Deep entity
    assert (test_graph["deep"].id, "entity") not in shallow_entities

    # With depth=2, we get the next level
    deep_results = await context_service.find_connected(type_id_pairs, max_depth=2)
    deep_entities = {(r.id, r.type) for r in deep_results if r.type == "entity"}
    # Should now include Deep entity
    assert (test_graph["deep"].id, "entity") in deep_entities


@pytest.mark.asyncio
async def test_find_connected_timeframe(context_service, test_graph, search_repository):
    """Test timeframe filtering.
    This tests how traversal is affected by the item dates.
    When we filter by date, items are only included if:
    1. They match the timeframe
    2. There is a valid path to them through other items in the timeframe
    """
    now = datetime.now(UTC)
    old_date = now - timedelta(days=10)
    recent_date = now - timedelta(days=1)

    # Index root and its relation as old
    await search_repository.index_item(
        id=test_graph["root"].id,
        title=test_graph["root"].title,
        content="Root content",
        permalink=test_graph["root"].permalink,
        file_path=test_graph["root"].file_path,
        type=SearchItemType.ENTITY,
        metadata={"created_at": old_date.isoformat()},
    )
    await search_repository.index_item(
        id=test_graph["relations"][0].id,
        title="Root Entity → Connected Entity 1",
        content="",
        permalink=f"{test_graph['root'].permalink}/connects_to/{test_graph['connected1'].permalink}",
        file_path=test_graph["root"].file_path,
        type=SearchItemType.RELATION,
        from_id=test_graph["root"].id,
        to_id=test_graph["connected1"].id,
        relation_type="connects_to",
        metadata={"created_at": old_date.isoformat()},
    )

    # Index connected1 as recent
    await search_repository.index_item(
        id=test_graph["connected1"].id,
        title=test_graph["connected1"].title,
        content="Connected 1 content",
        permalink=test_graph["connected1"].permalink,
        file_path=test_graph["connected1"].file_path,
        type=SearchItemType.ENTITY,
        metadata={"created_at": recent_date.isoformat()},
    )

    type_id_pairs = [("entity", test_graph["root"].id)]

    # Search with a 7-day cutoff
    since_date = now - timedelta(days=7)
    results = await context_service.find_connected(type_id_pairs, since=since_date)

    # Only connected1 is recent, but we can't get to it
    # because its connecting relation is too old
    entity_ids = {r.id for r in results if r.type == "entity"}
    assert len(entity_ids) == 0  # No accessible entities within timeframe


@pytest.mark.asyncio
async def test_build_context_pattern(context_service, test_graph):
    """Test building context from pattern."""
    context = await context_service.build_context("memory://project/test/*")
    assert len(context["primary_entities"]) > 0
    assert "uri" in context["metadata"]
    assert "total_entities" in context["metadata"]


@pytest.mark.asyncio
async def test_build_context_related(context_service, test_graph):
    """Test building context from related mode."""
    context = await context_service.build_context("memory://project/related/test/root")
    assert len(context["primary_entities"]) > 0
    assert len(context["related_entities"]) > 0


@pytest.mark.asyncio
async def test_build_context_not_found(context_service):
    """Test handling non-existent permalinks."""
    context = await context_service.build_context("memory://project/does/not/exist")
    assert len(context["primary_entities"]) == 0
    assert len(context["related_entities"]) == 0


@pytest.mark.asyncio
async def test_context_metadata(context_service, test_graph):
    """Test metadata is correctly populated."""
    context = await context_service.build_context("memory://project/test/root", depth=2)
    metadata = context["metadata"]
    assert metadata["uri"] == "memory://project/test/root"
    assert metadata["depth"] == 2
    assert metadata["generated_at"] is not None
    assert metadata["matched_entities"] > 0
