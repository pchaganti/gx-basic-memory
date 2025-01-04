import pytest
from datetime import datetime, timezone

import pytest_asyncio
from sqlalchemy import text

from basic_memory import db
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.schemas.search import SearchQuery
from basic_memory.services.search_service import SearchService

@pytest_asyncio.fixture
async def search_repository(session_maker):
    """Create SearchRepository instance"""
    return SearchRepository(session_maker)

@pytest_asyncio.fixture
async def search_service(search_repository: SearchRepository):
    """Create and initialize search service"""
    service = SearchService(search_repository)
    await service.init_search_index()
    return service

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

@pytest.mark.asyncio
async def test_search_filtering(search_service, test_entity):
    """Test search with filters"""
    await search_service.index_entity(test_entity)

    # Search with type filter
    results = await search_service.search(
        SearchQuery(
            text="test",
            types=["entity"],
            entity_types=["component"]
        )
    )
    assert len(results) == 1

    # Search with wrong type (should return no results)
    results = await search_service.search(
        SearchQuery(
            text="test",
            types=["document"]
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