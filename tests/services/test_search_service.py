"""Tests for search service fuzzy matching."""

import pytest
from datetime import datetime, timezone

from sqlalchemy import text

from basic_memory import db
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.schemas.search import SearchQuery, SearchItemType


@pytest.fixture
def test_entity():
    """Create a test entity"""
    class Entity:
        id = 1
        title = "TestComponent"
        entity_type = "knowledge"
        entity_metadata = {"test": "test"}
        permalink = "component/test_component"
        file_path = "entities/component/test_component.md"
        summary = "A test component for search"
        content_type = "text/markdown"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        observations = []
        relations = []

    return Entity()

@pytest.fixture
async def test_entities(search_service):
    """Create a set of test entities with variations."""
    entities = [
        # Core services
        type("Entity", (), {
            "id": 1,
            "title": "Core Service",
            "entity_type": "component",
            "permalink": "components/core-service",
            "file_path": "components/core-service.md",
            "content_type": "text/markdown",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "observations": [],
            "relations": [],
            "summary": "The core service implementation",
            "entity_metadata": {}
        })(),
        # Auth service
        type("Entity", (), {
            "id": 2,
            "title": "Auth Service",
            "entity_type": "component",
            "permalink": "components/auth/service",
            "file_path": "components/auth/service.md",
            "content_type": "text/markdown",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "observations": [],
            "relations": [],
            "summary": "Authentication service",
            "entity_metadata": {}
        })(),
        # Config service
        type("Entity", (), {
            "id": 3,
            "title": "Service Config",
            "entity_type": "config",
            "permalink": "config/service-config",
            "file_path": "config/service-config.md",
            "content_type": "text/markdown",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "observations": [],
            "relations": [],
            "summary": "Service configuration",
            "entity_metadata": {}
        })(),
        # Features doc
        type("Entity", (), {
            "id": 4,
            "title": "Core Features",
            "entity_type": "specs",
            "permalink": "specs/features/core",
            "file_path": "specs/features/core.md",
            "content_type": "text/markdown",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "observations": [],
            "relations": [],
            "summary": "Core feature specifications",
            "entity_metadata": {}
        })()
    ]
    
    # Index all entities
    for entity in entities:
        await search_service.index_entity(entity)
        
    return entities


@pytest.mark.asyncio
async def test_exact_match(search_service, test_entities):
    """Test exact matching of titles."""
    results = await search_service.search(SearchQuery(text="Core Service"))
    assert len(results) == 1
    assert results[0].permalink == "components/core-service"


@pytest.mark.asyncio
async def test_partial_match(search_service, test_entities):
    """Test partial matching of titles."""
    results = await search_service.search(SearchQuery(text="Auth Serv"))
    assert len(results) == 1
    assert results[0].permalink == "components/auth/service"


@pytest.mark.asyncio
async def test_misspelling_match(search_service, test_entities):
    """Test matching with misspellings."""
    results = await search_service.search(SearchQuery(text="Core Servise"))
    assert len(results) == 1
    assert results[0].permalink == "components/core-service"


@pytest.mark.asyncio
async def test_multiple_results_ranking(search_service, test_entities):
    """Test result ranking with multiple matches."""
    # Search for 'service' - should find multiple but rank appropriately
    results = await search_service.search(SearchQuery(text="service"))
    assert len(results) > 1
    # Auth service should rank higher than core service
    auth_idx = next(i for i, r in enumerate(results) if r.permalink == "components/auth/service")
    core_idx = next(i for i, r in enumerate(results) if r.permalink == "components/core-service")
    assert auth_idx < core_idx  # Lower index = better rank


@pytest.mark.asyncio
async def test_directory_context(search_service, test_entities):
    """Test matching with directory context."""
    results = await search_service.search(
        SearchQuery(text="Core"),
        context=["components/"]  # Should prefer matches in components/
    )
    assert len(results) > 0
    assert results[0].permalink.startswith("components/")


# Original test_init_search_index
@pytest.mark.asyncio
async def test_init_search_index(search_service, session_maker):
    """Test search index initialization"""
    async with db.scoped_session(session_maker) as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index';")
        )
        assert result.scalar() == "search_index"


# Original test_index_entity
@pytest.mark.asyncio
async def test_index_entity(search_service, test_entity):
    """Test indexing an entity"""
    await search_service.index_entity(test_entity)

    # Search for the entity
    results = await search_service.search(SearchQuery(text="test component"))
    assert len(results) == 1
    assert results[0].permalink == test_entity.permalink
    assert results[0].type == SearchItemType.ENTITY


# Original test_search_filtering
@pytest.mark.asyncio
async def test_search_filtering(search_service, test_entity):
    """Test search with filters"""
    await search_service.index_entity(test_entity)

    # Search with type filter
    results = await search_service.search(
        SearchQuery(text="test", types=[SearchItemType.ENTITY], entity_types=["knowledge"])
    )
    assert len(results) == 1

    # Search with wrong type (should return no results)
    results = await search_service.search(SearchQuery(text="test", types=[SearchItemType.DOCUMENT]))
    assert len(results) == 0


# Original test_update_index
@pytest.mark.asyncio
async def test_update_index(search_service, test_entity):
    """Test updating indexed content"""
    await search_service.index_entity(test_entity)

    # Update entity
    test_entity.summary = "Updated description with new terms"
    await search_service.index_entity(test_entity)

    # Search for new terms
    results = await search_service.search(SearchQuery(text="new terms"))
    assert len(results) == 1


# Original test_search_date_filter
@pytest.mark.asyncio
async def test_search_date_filter(search_service, test_entity):
    """Test searching with date filter"""
    await search_service.index_entity(test_entity)

    # Search with future date (should return no results)
    future = datetime.now(timezone.utc).replace(year=2026)
    results = await search_service.search(SearchQuery(text="test", after_date=future))
    assert len(results) == 0


# Original test_reindex_all
@pytest.mark.asyncio
async def test_reindex_all(search_service, entity_service, session_maker):
    """Test reindexing all content."""
    # Create test entities and documents
    test_entity = await entity_service.create_entity(
        EntitySchema(
            title="TestComponent",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
    )

    # Clear the search index
    async with db.scoped_session(session_maker) as session:
        await session.execute(text("DELETE FROM search_index"))
        await session.commit()

    # Verify nothing is searchable
    results = await search_service.search(SearchQuery(text="test"))
    assert len(results) == 0

    # Reindex everything
    await search_service.reindex_all()

    # Verify entity is searchable
    entity_results = await search_service.search(
        SearchQuery(text="TestComponent", types=[SearchItemType.ENTITY])
    )
    assert len(entity_results) == 1
    assert entity_results[0].permalink == test_entity.permalink
    assert entity_results[0].type == SearchItemType.ENTITY


# Original test_reindex_with_background_tasks
@pytest.mark.asyncio
async def test_reindex_with_background_tasks(search_service, entity_service, session_maker):
    """Test reindexing with background tasks."""
    from fastapi import BackgroundTasks

    # Create test data
    await entity_service.create_entity(
        EntitySchema(
            title="TestEntity1",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
    )

    # Clear index
    async with db.scoped_session(session_maker) as session:
        await session.execute(text("DELETE FROM search_index"))
        await session.commit()

    # Create background tasks
    background_tasks = BackgroundTasks()

    # Reindex with background tasks
    await search_service.reindex_all(background_tasks=background_tasks)

    # Execute background tasks
    await background_tasks()

    # Verify everything was indexed
    all_results = await search_service.search(SearchQuery(text="test"))
    assert len(all_results) == 1