"""Tests for search service fuzzy matching."""

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
async def test_exact_title_match(indexed_search):
    """Test exact title matching."""
    results = await indexed_search.search(SearchQuery(text="Core Service"))
    assert len(results) == 1
    assert results[0].file_path == "components/core-service.md"


@pytest.mark.asyncio
async def test_fuzzy_title_match_misspelling(indexed_search):
    """Test fuzzy matching with misspellings."""
    test_cases = [
        ("Core Servise", "components/core-service.md"),  # Common misspelling
        ("Auth Servise", "components/auth/service.md"),  # Another misspelling
        ("Core Servis", "components/core-service.md"),   # Partial word
        ("Srvc Config", "config/service-config.md"),     # Vowel omission
    ]
    
    for search_text, expected_path in test_cases:
        results = await indexed_search.search(SearchQuery(text=search_text))
        assert len(results) > 0, f"No results found for '{search_text}'"
        assert results[0].file_path == expected_path, f"Wrong match for '{search_text}'"


@pytest.mark.asyncio
async def test_partial_word_matching(indexed_search):
    """Test matching with partial words."""
    test_cases = [
        ("Auth Serv", "components/auth/service.md"),    # Partial service name
        ("Core Feat", "specs/features/core.md"),        # Partial feature word
        ("API Doc", "docs/api/documentation.md"),       # Abbreviated terms
    ]
    
    for search_text, expected_path in test_cases:
        results = await indexed_search.search(SearchQuery(text=search_text))
        assert len(results) > 0, f"No results found for '{search_text}'"
        assert results[0].file_path == expected_path, f"Wrong match for '{search_text}'"


@pytest.mark.asyncio
async def test_path_aware_matching(indexed_search):
    """Test path-aware matching preferences."""
    test_cases = [
        # Search text, context path, expected result
        ("Service", "components/other-service.md", "components/"),  # Should prefer component directory
        ("Core", "specs/features/other.md", "specs/features/"),     # Should prefer specs directory
        ("Service", None, "components/core-service.md"),            # No context, should pick highest scored
    ]
    
    for search_text, context, expected_prefix in test_cases:
        results = await indexed_search.search(
            SearchQuery(text=search_text),
            context=[context] if context else None
        )
        assert len(results) > 0, f"No results found for '{search_text}'"
        assert results[0].file_path.startswith(expected_prefix), \
            f"Wrong directory preference for '{search_text}' with context '{context}'"


@pytest.mark.asyncio
async def test_multi_word_fuzzy_matching(indexed_search):
    """Test fuzzy matching with multiple words."""
    test_cases = [
        ("Core Srvc", "components/core-service.md"),     # Multiple partial words
        ("Auth Srvice", "components/auth/service.md"),   # One full, one partial
        ("Cor Serv", "components/core-service.md"),      # Both partial
    ]
    
    for search_text, expected_path in test_cases:
        results = await indexed_search.search(SearchQuery(text=search_text))
        assert len(results) > 0, f"No results found for '{search_text}'"
        assert results[0].file_path == expected_path, f"Wrong match for '{search_text}'"


@pytest.mark.asyncio
async def test_word_order_invariance(indexed_search):
    """Test that word order doesn't affect matching."""
    test_cases = [
        ("Service Core", "components/core-service.md"),   # Reversed order
        ("Config Service", "config/service-config.md"),   # Reversed order
        ("Service Auth", "components/auth/service.md"),   # Reversed order
    ]
    
    for search_text, expected_path in test_cases:
        results = await indexed_search.search(SearchQuery(text=search_text))
        assert len(results) > 0, f"No results found for '{search_text}'"
        assert results[0].file_path == expected_path, f"Wrong match for '{search_text}'"


@pytest.mark.asyncio
async def test_relevance_scoring(indexed_search):
    """Test that relevance scoring works correctly."""
    # Search for "service" which should match multiple items
    results = await indexed_search.search(SearchQuery(text="service"))
    
    # Extract paths for easier assertion
    paths = [r.file_path for r in results]
    
    # Verify core service comes before service config (should have better score)
    core_idx = paths.index("components/core-service.md")
    config_idx = paths.index("config/service-config.md")
    assert core_idx < config_idx, "Core service should rank higher than service config"


@pytest.mark.asyncio
async def test_combined_search_criteria(indexed_search):
    """Test combining fuzzy search with other search criteria."""
    results = await indexed_search.search(
        SearchQuery(
            text="Core Serv",  # Fuzzy terms
            types=[SearchItemType.ENTITY],
            entity_types=["component"]
        )
    )
    
    assert len(results) == 1
    assert results[0].file_path == "components/core-service.md"


@pytest.mark.asyncio
async def test_index_variants_generation(search_service, entity_service):
    """Test that index variants are generated correctly."""
    # Create an entity with specific characteristics to test variant generation
    entity = await entity_service.create_entity(
        EntitySchema(
            title="Test-Component Service",
            entity_type="component",
            summary="A test component",
            file_path="components/test-component/service.md",
        )
    )
    
    await search_service.index_entity(entity)
    
    # Test various forms of the same content
    test_cases = [
        "test component",    # Lowercase without hyphen
        "Test-Component",    # Original form
        "test-comp",        # Partial with hyphen
        "TestComp",         # CamelCase partial
        "component/serv",    # Path segment with partial
    ]
    
    for search_text in test_cases:
        results = await search_service.search(SearchQuery(text=search_text))
        assert len(results) > 0, f"No results found for '{search_text}'"
        assert results[0].file_path == "components/test-component/service.md"


# Keep the original basic test fixtures
@pytest_asyncio.fixture
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
def test_document():
    """Create a test document"""
    class Document:
        id = 1
        permalink = "docs/test_doc.md"
        file_path = "docs/test_doc.md"
        doc_metadata = {"title": "Test Document", "type": "technical"}
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
    return Document()


# Keep the original basic tests
@pytest.mark.asyncio
async def test_init_search_index(search_service, session_maker):
    """Test search index initialization"""
    async with db.scoped_session(session_maker) as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index';")
        )
        assert result.scalar() == "search_index"


@pytest.mark.asyncio
async def test_index_entity(search_service, test_entity):
    """Test indexing an entity"""
    await search_service.index_entity(test_entity)
    results = await search_service.search(SearchQuery(text="test component"))
    assert len(results) == 1
    assert results[0].permalink == test_entity.permalink
    assert results[0].type == SearchItemType.ENTITY


@pytest.mark.asyncio
async def test_search_filtering(search_service, test_entity):
    """Test search with filters"""
    await search_service.index_entity(test_entity)
    results = await search_service.search(
        SearchQuery(text="test", types=[SearchItemType.ENTITY], entity_types=["knowledge"])
    )
    assert len(results) == 1
    results = await search_service.search(SearchQuery(text="test", types=[SearchItemType.DOCUMENT]))
    assert len(results) == 0


@pytest.mark.asyncio
async def test_update_index(search_service, test_entity):
    """Test updating indexed content"""
    await search_service.index_entity(test_entity)
    test_entity.summary = "Updated description with new terms"
    await search_service.index_entity(test_entity)
    results = await search_service.search(SearchQuery(text="new terms"))
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_date_filter(search_service, test_entity):
    """Test searching with date filter"""
    await search_service.index_entity(test_entity)
    future = datetime.now(timezone.utc).replace(year=2026)
    results = await search_service.search(SearchQuery(text="test", after_date=future))
    assert len(results) == 0


@pytest.mark.asyncio
async def test_reindex_all(search_service, entity_service, session_maker):
    """Test reindexing all content."""
    test_entity = await entity_service.create_entity(
        EntitySchema(
            title="TestComponent",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
    )

    async with db.scoped_session(session_maker) as session:
        await session.execute(text("DELETE FROM search_index"))
        await session.commit()

    results = await search_service.search(SearchQuery(text="test"))
    assert len(results) == 0

    await search_service.reindex_all()

    entity_results = await search_service.search(
        SearchQuery(text="TestComponent", types=[SearchItemType.ENTITY])
    )
    assert len(entity_results) == 1
    assert entity_results[0].permalink == test_entity.permalink
    assert entity_results[0].type == SearchItemType.ENTITY


@pytest.mark.asyncio
async def test_reindex_with_background_tasks(search_service, entity_service, session_maker):
    """Test reindexing with background tasks."""
    from fastapi import BackgroundTasks

    await entity_service.create_entity(
        EntitySchema(
            title="TestEntity1",
            entity_type="test",
            summary="A test entity description",
            observations=["this is a test observation"],
        ),
    )

    async with db.scoped_session(session_maker) as session:
        await session.execute(text("DELETE FROM search_index"))
        await session.commit()

    background_tasks = BackgroundTasks()
    await search_service.reindex_all(background_tasks=background_tasks)
    await background_tasks()

    all_results = await search_service.search(SearchQuery(text="test"))
    assert len(all_results) == 1