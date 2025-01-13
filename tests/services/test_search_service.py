"""Tests for search service."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from basic_memory import db
from basic_memory.models import Entity
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.schemas.search import SearchQuery, SearchItemType


@pytest_asyncio.fixture
async def test_entities(entity_repository):
    """Create a set of test entities with various naming patterns."""
    entities = [
        Entity(
            title="Core Service",
            entity_type="component",
            permalink="core-service",
            summary="The core service implementation",
            file_path="components/core-service.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Service Config",
            entity_type="config",
            permalink="service-config",
            summary="Configuration for services",
            file_path="config/service-config.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Auth Service",
            entity_type="component",
            permalink="auth-service",
            summary="Authentication service implementation",
            file_path="components/auth/service.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Core Features",
            entity_type="specs",
            permalink="core-features",
            summary="Core feature specifications",
            file_path="specs/features/core.md",
            content_type="text/markdown",
        ),
        Entity(
            title="API Documentation",
            entity_type="docs",
            permalink="api-documentation",
            summary="API documentation and examples",
            file_path="docs/api/documentation.md",
            content_type="text/markdown",
        )
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
async def test_basic_text_search(indexed_search):
    """Test basic search functionality works as expected."""
    # Test exact word match
    results = await indexed_search.search(SearchQuery(text="API"))
    assert len(results) == 1
    assert results[0].file_path == "docs/api/documentation.md"

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
        "  API  ",             # Extra spaces
        "API Documentation",         # Normal spacing
        "API    Documentation",       # Multiple spaces
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
        SearchQuery(
            text="service",
            types=[SearchItemType.ENTITY],
            entity_types=["component"]
        )
    )
    assert len(results) == 1
    assert results[0].file_path == "components/core-service.md"

    # Search with non-matching type (should return empty)
    results = await indexed_search.search(
        SearchQuery(
            text="service",
            types=[SearchItemType.DOCUMENT]
        )
    )
    assert len(results) == 0


# Basic operation tests
@pytest_asyncio.fixture
def test_entity():
    """Create a basic test entity."""
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


@pytest.mark.asyncio
async def test_init_search_index(search_service, session_maker):
    """Test search index initialization."""
    async with db.scoped_session(session_maker) as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index';")
        )
        assert result.scalar() == "search_index"


@pytest.mark.asyncio
async def test_update_index(search_service, test_entity):
    """Test updating indexed content."""
    await search_service.index_entity(test_entity)
    
    # Update entity
    test_entity.summary = "Updated description with new terms"
    await search_service.index_entity(test_entity)
    
    # Search for new terms
    results = await search_service.search(SearchQuery(text="new terms"))
    assert len(results) == 1