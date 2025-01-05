import pytest
from datetime import datetime, timezone

import pytest_asyncio
from sqlalchemy import text

from basic_memory import db
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.schemas.search import SearchQuery, SearchItemType
from basic_memory.services.search_service import SearchService


@pytest.fixture
def test_entity():
    """Create a test entity"""
    class Entity:
        id = 1
        name = "TestComponent"
        entity_type = "component"
        path_id = "component/test_component"
        file_path = "entities/component/test_component.md"
        description = "A test component for search"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        observations = []
        relations = []
    return Entity()


@pytest.fixture
def test_document():
    """Create a test document"""
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


@pytest.mark.asyncio
async def test_init_search_index(search_service, session_maker):
    """Test search index initialization"""
    # Check that table exists
    async with db.scoped_session(session_maker) as session:
        result = await session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='search_index';"
        ))
        assert result.scalar() == "search_index"


@pytest.mark.asyncio
async def test_index_entity(search_service, test_entity):
    """Test indexing an entity"""
    await search_service.index_entity(test_entity)

    # Search for the entity
    results = await search_service.search(SearchQuery(text="test component"))
    assert len(results) == 1
    assert results[0].path_id == test_entity.path_id
    assert results[0].type == SearchItemType.ENTITY


@pytest.mark.asyncio
async def test_search_filtering(search_service, test_entity):
    """Test search with filters"""
    await search_service.index_entity(test_entity)

    # Search with type filter
    results = await search_service.search(
        SearchQuery(
            text="test",
            types=[SearchItemType.ENTITY],
            entity_types=["component"]
        )
    )
    assert len(results) == 1

    # Search with wrong type (should return no results)
    results = await search_service.search(
        SearchQuery(
            text="test",
            types=[SearchItemType.DOCUMENT]
        )
    )
    assert len(results) == 0


@pytest.mark.asyncio
async def test_update_index(search_service, test_entity):
    """Test updating indexed content"""
    await search_service.index_entity(test_entity)

    # Update entity
    test_entity.description = "Updated description with new terms"
    await search_service.index_entity(test_entity)

    # Search for new terms
    results = await search_service.search(SearchQuery(text="new terms"))
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_date_filter(search_service, test_entity):
    """Test searching with date filter"""
    await search_service.index_entity(test_entity)

    # Search with future date (should return no results)
    future = datetime.now(timezone.utc).replace(year=2026)
    results = await search_service.search(
        SearchQuery(
            text="test",
            after_date=future
        )
    )
    assert len(results) == 0


@pytest.mark.asyncio
async def test_index_document(search_service, test_document):
    """Test indexing a document"""
    content = """# Test Document
    
This is a test document with some searchable content.
It contains technical information about implementation."""

    await search_service.index_document(test_document, content)

    # Search for document content
    results = await search_service.search(SearchQuery(text="searchable content"))
    assert len(results) == 1
    assert results[0].path_id == test_document.path_id
    assert results[0].type == SearchItemType.DOCUMENT
    
    # Verify metadata
    assert results[0].metadata["title"] == "Test Document"
    assert results[0].metadata["type"] == "technical"


@pytest.mark.asyncio
async def test_update_document_index(search_service, test_document):
    """Test updating an indexed document"""
    # Initial indexing
    await search_service.index_document(test_document, "Initial content")

    # Update with new content
    await search_service.index_document(test_document, "Updated content with new terms")

    # Search for new terms
    results = await search_service.search(SearchQuery(text="new terms"))
    assert len(results) == 1