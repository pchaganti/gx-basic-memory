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
async def test_basic_text_search(indexed_search, test_entities):
    """Test basic search functionality works as expected."""
    # Test exact word match
    results = await indexed_search.search(SearchQuery(text="API"))
    assert len(results) == 1
    assert results[0].file_path == "docs/api/documentation.md"
    assert results[0].id == test_entities[-1].id

    # Test prefix match (serv should match service)
    results = await indexed_search.search(SearchQuery(text="Serv"))
    assert len(results) > 0
    assert any(r.file_path == "components/core-service.md" for r in results)


@pytest.mark.asyncio
async def test_case_insensitive_search(indexed_search):
    """Test that search is case insensitive."""
    test_cases = [
        "core",
        "CORE",
        "Core",
    ]
    for search_text in test_cases:
        results = await indexed_search.search(SearchQuery(text=search_text))
        assert len(results) == 2, f"Failed for '{search_text}'"

        file_paths = [r.file_path for r in results]
        assert "components/core-service.md" in file_paths
        assert "specs/features/core.md" in file_paths


@pytest.mark.asyncio
async def test_whitespace_handling(indexed_search):
    """Test that whitespace is handled correctly."""
    test_cases = [
        "  API  ",  # Extra spaces
        "API Documentation",  # Normal spacing
        "API    Documentation",  # Multiple spaces
    ]
    for search_text in test_cases:
        results = await indexed_search.search(SearchQuery(text=search_text))
        assert len(results) == 1, f"Failed for '{search_text}'"
        assert results[0].file_path == "docs/api/documentation.md"


@pytest.mark.asyncio
async def test_content_search(indexed_search):
    """Test searching in content/summary field."""
    # Test matching against summary text
    results = await indexed_search.search(SearchQuery(text="implementation"))
    assert len(results) == 2

    file_paths = [r.file_path for r in results]
    assert "components/core-service.md" in file_paths
    assert "components/auth/service.md" in file_paths


@pytest.mark.asyncio
async def test_search_filters(indexed_search):
    """Test search filtering."""
    # Search with correct type filter
    results = await indexed_search.search(
        SearchQuery(text="service", types=[SearchItemType.ENTITY], entity_types=["component"])
    )
    assert len(results) == 2

    file_paths = [r.file_path for r in results]
    assert "components/core-service.md" in file_paths
    assert "components/auth/service.md" in file_paths

    # Search with non-matching type (should return empty)
    results = await indexed_search.search(
        SearchQuery(text="service", types=[SearchItemType.RELATION])
    )
    assert len(results) == 0


@pytest.mark.asyncio
async def test_path_pattern_search(indexed_search):
    """Test path pattern matching in permalinks."""
    # Test exact path match
    results = await indexed_search.search(
        SearchQuery(permalink="components/core-service")
    )
    assert len(results) == 1
    assert results[0].permalink == "components/core-service"

    # Test prefix matching with *
    results = await indexed_search.search(
        SearchQuery(permalink="components/*")
    )
    assert len(results) == 2  # Should match both core-service and auth/service
    permalinks = {r.permalink for r in results}
    assert "components/core-service" in permalinks
    assert "components/auth/service" in permalinks

    # Test nested path matching
    results = await indexed_search.search(
        SearchQuery(permalink="components/*/service")
    )
    permalinks = [r.permalink for r in results]
    assert len(permalinks) == 2
    assert "components/auth/service" in permalinks
    assert "components/core-service" in permalinks

    # Test top-level pattern
    results = await indexed_search.search(
        SearchQuery(permalink="*/service")
    )
    permalinks = [r.permalink for r in results]
    assert len(permalinks) == 3
    assert "components/auth/service" in permalinks
    assert "components/core-service" in permalinks
    assert "config/service-config" in permalinks


@pytest.mark.asyncio
async def test_init_search_index(search_service, session_maker):
    """Test search index initialization."""
    async with db.scoped_session(session_maker) as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index';")
        )
        assert result.scalar() == "search_index"


@pytest.mark.asyncio
async def test_update_index(search_service, full_entity):
    """Test updating indexed content."""
    await search_service.index_entity(full_entity)

    # Update entity
    full_entity.summary = "Updated description with new terms"
    await search_service.index_entity(full_entity)

    # Search for new terms
    results = await search_service.search(SearchQuery(text="new terms"))
    assert len(results) == 1