"""Tests for search router."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from basic_memory import db
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.schemas.search import SearchItemType, SearchResponse


@pytest.fixture
def test_entity():
    """Create a test entity."""

    class Entity:
        id = 1
        title = "TestComponent"
        entity_type = "test"
        entity_metadata = {"test": "test"}
        permalink = "component/test_component"
        file_path = "entities/component/test_component.md"
        summary = "A test component for search testing"
        content_type = "text/markdown"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        observations = []
        relations = []

    return Entity()


@pytest_asyncio.fixture
async def indexed_entity(init_search_index, test_entity, search_service):
    """Create an entity and index it."""
    await search_service.index_entity(test_entity)
    return test_entity


@pytest.mark.asyncio
async def test_search_basic(client, indexed_entity):
    """Test basic text search."""
    response = await client.post("/search/", json={"text": "test component"})
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1
    assert search_results.results[0].permalink == indexed_entity.permalink


@pytest.mark.asyncio
async def test_search_with_type_filter(client, indexed_entity):
    """Test search with type filter."""
    # Should find with correct type
    response = await client.post(
        "/search/", json={"text": "test", "types": [SearchItemType.ENTITY.value]}
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1

    # Should not find with wrong type
    response = await client.post(
        "/search/", json={"text": "test", "types": [SearchItemType.DOCUMENT.value]}
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0


@pytest.mark.asyncio
async def test_search_with_entity_type_filter(client, indexed_entity):
    """Test search with entity type filter."""
    # Should find with correct entity type
    response = await client.post("/search/", json={"text": "test", "entity_types": ["test"]})
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1

    # Should not find with wrong entity type
    response = await client.post("/search/", json={"text": "test", "entity_types": ["note"]})
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0


@pytest.mark.asyncio
async def test_search_with_date_filter(client, indexed_entity):
    """Test search with date filter."""
    # Should find with past date
    past_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    response = await client.post(
        "/search/", json={"text": "test", "after_date": past_date.isoformat()}
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1

    # Should not find with future date
    future_date = datetime(2030, 1, 1, tzinfo=timezone.utc)
    response = await client.post(
        "/search/", json={"text": "test", "after_date": future_date.isoformat()}
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0

@pytest.mark.skip("search scoring is not implemented yet")
@pytest.mark.asyncio
async def test_search_scoring(client, indexed_entity):
    """Test search result scoring."""
    # Exact match should score higher
    exact_response = await client.post("/search/", json={"text": "TestComponent"})

    # Partial match should score lower
    partial_response = await client.post("/search/", json={"text": "test"})

    assert exact_response.status_code == 200
    assert partial_response.status_code == 200

    exact_result = SearchResponse.model_validate(exact_response.json())
    partial_result = SearchResponse.model_validate(partial_response.json())

    exact_score = exact_result.results[0].score
    partial_score = partial_result.results[0].score

    assert exact_score > partial_score


@pytest.mark.asyncio
async def test_search_empty(search_service, client):
    """Test search with no matches."""
    response = await client.post("/search/", json={"text": "nonexistent"})
    assert response.status_code == 200
    search_result = SearchResponse.model_validate(response.json())
    assert len(search_result.results) == 0


@pytest.mark.asyncio
async def test_reindex(client, search_service, entity_service, test_entity, session_maker):
    """Test reindex endpoint."""
    # Create test entity and document
    await entity_service.create_entity(
        EntitySchema(
            title="TestEntity1",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
    )

    # Clear search index
    async with db.scoped_session(session_maker) as session:
        await session.execute(text("DELETE FROM search_index"))
        await session.commit()

    # Verify nothing is searchable
    response = await client.post("/search/", json={"text": "test"})
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0

    # Trigger reindex
    reindex_response = await client.post("/search/reindex")
    assert reindex_response.status_code == 200
    assert reindex_response.json()["status"] == "ok"

    # Verify content is searchable again
    search_response = await client.post("/search/", json={"text": "test"})
    search_results = SearchResponse.model_validate(search_response.json())
    assert len(search_results.results) == 1


@pytest.mark.asyncio
async def test_multiple_filters(client, indexed_entity):
    """Test search with multiple filters combined."""
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": [SearchItemType.ENTITY.value],
            "entity_types": ["test"],
            "after_date": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 200
    search_result = SearchResponse.model_validate(response.json())
    assert len(search_result.results) == 1
    result = search_result.results[0]
    assert result.permalink == indexed_entity.permalink
    assert result.type == SearchItemType.ENTITY.value
    assert result.metadata["entity_type"] == "test"
