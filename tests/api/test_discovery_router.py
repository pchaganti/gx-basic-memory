"""Tests for discovery router endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from basic_memory.models.knowledge import Entity, Observation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import EntityTypeList, ObservationCategoryList, TypedEntityList

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def test_entities(entity_repository: EntityRepository) -> list[Entity]:
    """Create test entities with different types."""
    entities = [
        Entity(
            title="Memory Service",
            entity_type="test",
            content_type="text/markdown",
            summary="Core memory service",
            permalink="component/memory_service",
            file_path="component/memory_service.md",
            observations=[
                Observation(category="tech", content="Using SQLite for storage"),
                Observation(category="design", content="Local-first architecture"),
            ],
        ),
        Entity(
            title="File Format",
            entity_type="test",
            content_type="text/markdown",
            summary="File format spec",
            permalink="spec/file_format",
            file_path="spec/file_format.md",
            observations=[
                Observation(category="feature", content="Support for frontmatter"),
                Observation(category="tech", content="UTF-8 encoding"),
            ],
        ),
        Entity(
            title="Technical Decision",
            entity_type="test",
            content_type="text/markdown",
            summary="Architecture decision",
            permalink="decision/tech_choice",
            file_path="decision/tech_choice.md",
            observations=[
                Observation(category="note", content="Team discussed options"),
                Observation(category="design", content="Selected for scalability"),
            ],
        ),
        # Add another technical component for sorting tests
        Entity(
            title="API Service",
            entity_type="test",
            content_type="text/markdown",
            summary="API layer",
            permalink="component/api_service",
            file_path="component/api_service.md",
            observations=[
                Observation(category="tech", content="FastAPI based"),
            ],
        ),
    ]

    created = await entity_repository.add_all(entities)
    return created


async def test_get_entity_types(client: AsyncClient, test_entities):
    """Test getting list of entity types."""
    # Get types
    response = await client.get("/discovery/entity-types")
    assert response.status_code == 200

    # Parse response
    data = EntityTypeList.model_validate(response.json())

    # Should have types from test data
    assert len(data.types) > 0
    assert "test" in data.types

    # Types should all be strings
    assert isinstance(data.types, list)
    assert all(isinstance(t, str) for t in data.types)

    # Types should be unique
    assert len(data.types) == len(set(data.types))


async def test_get_observation_categories(client: AsyncClient, test_entities):
    """Test getting list of observation categories."""
    # Get categories
    response = await client.get("/discovery/observation-categories")
    assert response.status_code == 200

    # Parse response
    data = ObservationCategoryList.model_validate(response.json())

    # Should have categories from test data
    assert len(data.categories) > 0
    assert "tech" in data.categories
    assert "design" in data.categories
    assert "feature" in data.categories
    assert "note" in data.categories

    # Categories should all be strings
    assert isinstance(data.categories, list)
    assert all(isinstance(c, str) for c in data.categories)

    # Categories should be unique
    assert len(data.categories) == len(set(data.categories))


async def test_list_entities_by_type(client: AsyncClient, test_entities):
    """Test listing entities by type."""
    # List technical components
    response = await client.get("/discovery/entities/test")
    assert response.status_code == 200

    # Parse response
    data = TypedEntityList.model_validate(response.json())

    # Check response structure
    assert data.entity_type == "test"
    assert len(data.entities) == 4
    assert data.total == 4

    # Verify content
    titles = {e.title for e in data.entities}
    assert "Memory Service" in titles
    assert "API Service" in titles


async def test_list_entities_with_sorting(client: AsyncClient, test_entities):
    """Test listing entities with different sort options."""
    # Sort by name
    response = await client.get("/discovery/entities/technical_component?sort_by=name")
    assert response.status_code == 200
    data = TypedEntityList.model_validate(response.json())
    names = [e.name for e in data.entities]
    assert names == sorted(names)  # Should be alphabetical

    # Sort by permalink
    response = await client.get("/discovery/entities/technical_component?sort_by=permalink")
    assert response.status_code == 200
    data = TypedEntityList.model_validate(response.json())
    permalinks = [e.permalink for e in data.entities]
    assert permalinks == sorted(permalinks)


async def test_list_entities_empty_type(client: AsyncClient, test_entities):
    """Test listing entities for a type that doesn't exist."""
    response = await client.get("/discovery/entities/nonexistent_type")
    assert response.status_code == 200

    data = TypedEntityList.model_validate(response.json())
    assert data.entity_type == "nonexistent_type"
    assert len(data.entities) == 0
    assert data.total == 0
