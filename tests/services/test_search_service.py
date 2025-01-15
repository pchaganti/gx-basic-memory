"""Tests for search service."""

import pytest
import pytest_asyncio
from sqlalchemy import text

from basic_memory import db
from basic_memory.models import Entity, Observation, ObservationCategory, Relation
from basic_memory.schemas.search import SearchQuery, SearchItemType


@pytest_asyncio.fixture
async def test_entities(entity_repository):
    """Create a set of test entities with various naming patterns."""
    entities = [
        Entity(
            title="Core Service",
            entity_type="component",
            permalink="components/core-service",  # Updated to use path-style permalinks
            summary="The core service implementation",
            file_path="components/core-service.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Service Config",
            entity_type="config",
            permalink="config/service-config",
            summary="Configuration for services",
            file_path="config/service-config.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Auth Service",
            entity_type="component",
            permalink="components/auth/service",  # Nested path
            summary="Authentication service implementation",
            file_path="components/auth/service.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Core Features",
            entity_type="specs",
            permalink="specs/features/core",
            summary="Core feature specifications",
            file_path="specs/features/core.md",
            content_type="text/markdown",
        ),
        Entity(
            title="API Documentation",
            entity_type="docs",
            permalink="docs/api/documentation", 
            summary="API documentation and examples",
            file_path="docs/api/documentation.md",
            content_type="text/markdown",
        ),
    ]

    return await entity_repository.add_all(entities)


@pytest_asyncio.fixture
async def indexed_search(search_service, test_entities):
    """Create SearchService instance with indexed test data."""
    # Index all test entities
    for entity in test_entities:
        await search_service.index_entity(entity)
    return search_service


@pytest.mark.asyncio
async def test_search_modes(indexed_search):
    """Test all three search modes work correctly."""
    # 1. Exact permalink
    results = await indexed_search.search(SearchQuery(permalink="components/core-service"))
    assert len(results) == 1
    assert results[0].permalink == "components/core-service"

    # 2. Pattern matching
    results = await indexed_search.search(SearchQuery(permalink_pattern="components/*"))
    assert len(results) == 2
    permalinks = {r.permalink for r in results}
    assert "components/core-service" in permalinks
    assert "components/auth/service" in permalinks

    # 3. Full-text search
    results = await indexed_search.search(SearchQuery(text="implementation"))
    assert len(results) >= 1
    assert any("service" in r.permalink for r in results)


@pytest.mark.asyncio
async def test_text_search_features(indexed_search):
    """Test text search functionality."""
    # Case insensitive
    results = await indexed_search.search(SearchQuery(text="API"))
    assert len(results) == 1
    assert results[0].file_path == "docs/api/documentation.md"

    # Partial word match
    results = await indexed_search.search(SearchQuery(text="Serv"))
    assert len(results) > 0
    assert any(r.file_path == "components/core-service.md" for r in results)

    # Multiple terms
    results = await indexed_search.search(SearchQuery(text="core service"))
    assert any("core-service" in r.permalink for r in results)


@pytest.mark.asyncio
async def test_pattern_matching(indexed_search):
    """Test pattern matching with various wildcards."""
    # Test nested wildcards
    results = await indexed_search.search(
        SearchQuery(permalink_pattern="components/*/service")
    )
    assert len(results) == 1  # Should match components/auth/service
    assert results[0].permalink == "components/auth/service"

    # Test start wildcards
    results = await indexed_search.search(
        SearchQuery(permalink_pattern="*/service")
    )
    assert len(results) == 1
    assert results[0].permalink == "components/auth/service"

    # Test end wildcards
    results = await indexed_search.search(
        SearchQuery(permalink_pattern="components/*")
    )
    assert len(results) == 2
    assert all("components/" in r.permalink for r in results)


@pytest.mark.asyncio
async def test_filters(indexed_search):
    """Test search filters."""
    # Filter by type
    results = await indexed_search.search(
        SearchQuery(
            text="service",
            types=[SearchItemType.ENTITY]
        )
    )
    assert all(r.type == SearchItemType.ENTITY for r in results)

    # Filter by entity type
    results = await indexed_search.search(
        SearchQuery(
            text="service",
            entity_types=["component"]
        )
    )
    assert all(r.metadata.get("entity_type") == "component" for r in results)

    # Combined filters
    results = await indexed_search.search(
        SearchQuery(
            text="service",
            types=[SearchItemType.ENTITY],
            entity_types=["component"]
        )
    )
    assert len(results) == 2
    assert all(r.type == SearchItemType.ENTITY for r in results)
    assert all(r.metadata.get("entity_type") == "component" for r in results)


@pytest.mark.asyncio
async def test_no_criteria(indexed_search):
    """Test search with no criteria returns empty list."""
    results = await indexed_search.search(SearchQuery())
    assert len(results) == 0


@pytest.mark.asyncio
async def test_init_search_index(search_service, session_maker):
    """Test search index initialization."""
    async with db.scoped_session(session_maker) as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index';")
        )
        assert result.scalar() == "search_index"


@pytest.mark.asyncio
async def test_update_index(indexed_search, full_entity):
    """Test updating indexed content."""
    await indexed_search.index_entity(full_entity)

    # Update entity
    full_entity.summary = "Updated description with new terms"
    await indexed_search.index_entity(full_entity)

    # Search for new terms
    results = await indexed_search.search(SearchQuery(text="new terms"))
    assert len(results) == 1