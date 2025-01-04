"""Tests for search router."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from basic_memory.schemas.search import SearchQuery
from basic_memory.services.search_service import SearchService



@pytest_asyncio.fixture
def test_entity():
    """Create a test entity."""
    class Entity:
        id = 1
        name = "TestComponent"
        entity_type = "component"
        path_id = "component/test_component"
        file_path = "entities/component/test_component.md"
        description = "A test component for search testing"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        observations = []
        relations = []
    return Entity()


@pytest_asyncio.fixture
async def indexed_entity(test_entity, search_service):
    """Create an entity and index it."""
    await search_service.index_entity(test_entity)
    return test_entity


@pytest.mark.asyncio
async def test_search_basic(client, indexed_entity):
    """Test basic text search."""
    response = await client.post(
        "/search/",
        json={
            "text": "test component"
        }
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["path_id"] == indexed_entity.path_id


@pytest.mark.asyncio
async def test_search_with_type_filter(client, indexed_entity):
    """Test search with type filter."""
    # Should find with correct type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": ["entity"]
        }
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    
    # Should not find with wrong type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": ["document"]
        }
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_search_with_entity_type_filter(client, indexed_entity):
    """Test search with entity type filter."""
    # Should find with correct entity type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "entity_types": ["component"]
        }
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    
    # Should not find with wrong entity type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "entity_types": ["concept"]
        }
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_search_with_date_filter(client, indexed_entity):
    """Test search with date filter."""
    # Should find with past date
    past_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "after_date": past_date.isoformat()
        }
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Should not find with future date
    future_date = datetime(2030, 1, 1, tzinfo=timezone.utc)
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "after_date": future_date.isoformat()
        }
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_search_scoring(client, indexed_entity):
    """Test search result scoring."""
    # Exact match should score higher
    exact_response = await client.post(
        "/search/",
        json={"text": "TestComponent"}
    )
    
    # Partial match should score lower
    partial_response = await client.post(
        "/search/",
        json={"text": "test"}
    )
    
    assert exact_response.status_code == 200
    assert partial_response.status_code == 200
    
    exact_score = exact_response.json()[0]["score"]
    partial_score = partial_response.json()[0]["score"]
    
    assert exact_score > partial_score


@pytest.mark.asyncio
async def test_search_empty(search_service, client):
    """Test search with no matches."""
    response = await client.post(
        "/search/",
        json={"text": "nonexistent"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_reindex(search_service, client):
    """Test reindex endpoint."""
    response = await client.post("/search/reindex")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_multiple_filters(client, indexed_entity):
    """Test search with multiple filters combined."""
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": ["entity"],
            "entity_types": ["component"],
            "after_date": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        }
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    result = results[0]
    assert result["path_id"] == indexed_entity.path_id
    assert result["type"] == "entity"
    assert result["metadata"]["entity_type"] == "component"