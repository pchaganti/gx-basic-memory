"""Tests for search router."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from basic_memory import db
from basic_memory.schemas import EntityType
from basic_memory.schemas.search import SearchQuery, SearchItemType, SearchResponse


@pytest.fixture
def test_entity():
    """Create a test entity."""
    class Entity:
        id = 1
        name = "TestComponent"
        entity_type = EntityType.KNOWLEDGE
        entity_metadata = { "test": "test"}
        path_id = "component/test_component"
        file_path = "entities/component/test_component.md"
        description = "A test component for search testing"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        observations = []
        relations = []
    return Entity()


@pytest.fixture
def test_document():
    """Create a test document."""
    class Document:
        id = 1
        path_id = "docs/test_doc.md"
        file_path = "docs/test_doc.md"
        doc_metadata = {
            "title": "Test Document",
            "type": "technical"
        }
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
    return Document()


@pytest_asyncio.fixture
async def indexed_entity(init_search_index, test_entity, search_service):
    """Create an entity and index it."""
    await search_service.index_entity(test_entity)
    return test_entity


@pytest.fixture
async def indexed_document(test_document, search_service):
    """Create a document and index it."""
    content = "Test document content for search"
    await search_service.index_document(test_document, content)
    return test_document, content


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
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1
    assert search_results.results[0].path_id == indexed_entity.path_id


@pytest.mark.asyncio
async def test_search_with_type_filter(client, indexed_entity):
    """Test search with type filter."""
    # Should find with correct type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": [SearchItemType.ENTITY.value]
        }
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1
    
    # Should not find with wrong type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": [SearchItemType.DOCUMENT.value]
        }
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0


@pytest.mark.asyncio
async def test_search_with_entity_type_filter(client, indexed_entity):
    """Test search with entity type filter."""
    # Should find with correct entity type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "entity_types": [EntityType.KNOWLEDGE]
        }
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1
    
    # Should not find with wrong entity type
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "entity_types": [EntityType.NOTE]
        }
    )
    assert response.status_code == 200
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0


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
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 1
    
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
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0


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

    exact_result = SearchResponse.model_validate(exact_response.json())
    partial_result = SearchResponse.model_validate(partial_response.json())
    
    exact_score = exact_result.results[0].score
    partial_score = partial_result.results[0].score
    
    assert exact_score > partial_score


@pytest.mark.asyncio
async def test_search_empty(search_service, client):
    """Test search with no matches."""
    response = await client.post(
        "/search/",
        json={"text": "nonexistent"}
    )
    assert response.status_code == 200
    search_result = SearchResponse.model_validate(response.json())
    assert len(search_result.results) == 0


@pytest.mark.asyncio
async def test_reindex(
    client,
    search_service,
    entity_service,
    document_service,
    test_entity,
    test_document,
    session_maker
):
    """Test reindex endpoint."""
    # Create test entity and document
    await entity_service.create_entity(test_entity)
    await document_service.create_document(
        test_document.path_id,
        "Test content",
        test_document.doc_metadata
    )

    # Clear search index
    async with db.scoped_session(session_maker) as session:
        await session.execute(text("DELETE FROM search_index"))
        await session.commit()

    # Verify nothing is searchable
    response = await client.post(
        "/search/",
        json={"text": "test"}
    )
    search_results = SearchResponse.model_validate(response.json())
    assert len(search_results.results) == 0

    # Trigger reindex
    reindex_response = await client.post("/search/reindex")
    assert reindex_response.status_code == 200
    assert reindex_response.json()["status"] == "ok"

    # Verify content is searchable again
    search_response = await client.post(
        "/search/",
        json={"text": "test"}
    )
    search_results = SearchResponse.model_validate(search_response.json())
    assert len(search_results.results) == 2  # Both entity and document should be found


@pytest.mark.asyncio
async def test_multiple_filters(client, indexed_entity):
    """Test search with multiple filters combined."""
    response = await client.post(
        "/search/",
        json={
            "text": "test",
            "types": [SearchItemType.ENTITY.value],
            "entity_types": [EntityType.KNOWLEDGE],
            "after_date": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        }
    )
    assert response.status_code == 200
    search_result = SearchResponse.model_validate(response.json())
    assert len(search_result.results) == 1
    result = search_result.results[0]
    assert result.path_id == indexed_entity.path_id
    assert result.type == SearchItemType.ENTITY.value
    assert result.metadata["entity_type"] == EntityType.KNOWLEDGE