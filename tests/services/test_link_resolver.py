"""Tests for link resolution service."""

import pytest
from datetime import datetime, timezone

import pytest_asyncio

from basic_memory.models.knowledge import Entity
from basic_memory.services.link_resolver import LinkResolver
from basic_memory.schemas.search import SearchQuery, SearchItemType


@pytest_asyncio.fixture
async def test_entities(entity_repository):
    """Create a set of test entities."""
    entities = [
        Entity(
            title="Core Service",
            entity_type="component",
            summary="The core service implementation",
            permalink="components/core-service",
            file_path="components/core-service.md",
            content_type="text/markdown",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Entity(
            title="Service Config",
            entity_type="config",
            summary="Configuration for services",
            permalink="config/service-config",
            file_path="config/service-config.md",
            content_type="text/markdown",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Entity(
            title="Auth Service",
            entity_type="component",
            summary="Authentication service implementation",
            permalink="components/auth/service",
            file_path="components/auth/service.md",
            content_type="text/markdown",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Entity(
            title="Core Features",
            entity_type="specs",
            summary="Core feature specifications",
            permalink="specs/features/core",
            file_path="specs/features/core.md",
            content_type="text/markdown",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]
    
    # Add to repository
    for entity in entities:
        await entity_repository.add(entity)
    
    return entities


@pytest_asyncio.fixture
async def link_resolver(entity_repository, search_service, test_entities):
    """Create LinkResolver instance with indexed test data."""
    # Index all test entities
    for entity in test_entities:
        await search_service.index_entity(entity)
    
    return LinkResolver(entity_repository, search_service)


@pytest.mark.asyncio
async def test_exact_permalink_match(link_resolver):
    """Test resolving a link that exactly matches a permalink."""
    result = await link_resolver.resolve_link("components/core-service")
    assert result == "components/core-service"


@pytest.mark.asyncio
async def test_exact_title_match(link_resolver):
    """Test resolving a link that matches an entity title."""
    result = await link_resolver.resolve_link("Core Service")
    assert result == "components/core-service"


@pytest.mark.asyncio
async def test_fuzzy_title_match_misspelling(link_resolver):
    # Test slight misspelling
    result = await link_resolver.resolve_link("Core Servise")
    assert result == "components/core-service"

@pytest.mark.asyncio
async def test_fuzzy_title_partial_match(link_resolver):
    # Test partial match
    result = await link_resolver.resolve_link("Auth Serv")
    assert result == "components/auth/service"


@pytest.mark.asyncio
async def test_context_aware_matching(link_resolver):
    """Test that matching considers source context."""
    # Should prefer match in components/ when source is in components/
    result = await link_resolver.resolve_link(
        "Service",  # Ambiguous - could match several
        source_permalink="components/other-service"
    )
    assert result.startswith("components/")
    
    # Should prefer match in specs/ when source is in specs/
    result = await link_resolver.resolve_link(
        "Core",  # Ambiguous - could match several
        source_permalink="specs/features/other"
    )
    assert result.startswith("specs/")


@pytest.mark.asyncio
async def test_link_text_normalization(link_resolver):
    """Test link text normalization."""
    # Basic normalization
    text, alias = link_resolver._normalize_link_text("[[Core Service]]")
    assert text == "Core Service"
    assert alias is None

    # With alias
    text, alias = link_resolver._normalize_link_text("[[Core Service|Main Service]]")
    assert text == "Core Service"
    assert alias == "Main Service"

    # Extra whitespace
    text, alias = link_resolver._normalize_link_text("  [[  Core Service  |  Main Service  ]]  ")
    assert text == "Core Service"
    assert alias == "Main Service"


@pytest.mark.asyncio
async def test_new_entity_permalink_generation(link_resolver):
    """Test generating permalink for non-existent entity."""
    # Basic new entity
    result = await link_resolver.resolve_link("New Feature")
    assert result == "new-feature"
    
    # With directory structure
    result = await link_resolver.resolve_link("components/New Feature")
    assert result == "components/new-feature"
    
    # With special characters
    result = await link_resolver.resolve_link("New Feature (v2)!!!")
    assert result == "new-feature-v2"


@pytest.mark.asyncio
async def test_multiple_matches_resolution(link_resolver):
    """Test resolution when multiple potential matches exist."""
    # Add some similar entities
    test_cases = [
        {
            "link": "Service",  # Ambiguous
            "source": "components/some-service",
            "expected_prefix": "components/"  # Should prefer component directory match
        },
        {
            "link": "Core",  # Ambiguous
            "source": "specs/features/other",
            "expected_prefix": "specs/"  # Should prefer specs directory match
        },
        {
            "link": "Service",
            "source": None,  # No context
            "expected": "components/core-service"  # Should pick shortest/highest scored
        }
    ]
    
    for case in test_cases:
        result = await link_resolver.resolve_link(case["link"], case["source"])
        if "expected_prefix" in case:
            assert result.startswith(case["expected_prefix"])
        else:
            assert result == case["expected"]