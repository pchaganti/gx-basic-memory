"""Tests for the ObservationService."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory.models import Entity, Observation
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.schemas.base import ObservationCategory
from basic_memory.schemas.request import ObservationCreate
from basic_memory.services.observation_service import ObservationService


@pytest_asyncio.fixture
async def observation_repository(
    session_maker: async_sessionmaker[AsyncSession],
) -> ObservationRepository:
    """Create an ObservationRepository instance."""
    return ObservationRepository(session_maker)


@pytest_asyncio.fixture
async def observation_service(observation_repository: ObservationRepository) -> ObservationService:
    """Create ObservationService with repository."""
    return ObservationService(observation_repository)


@pytest_asyncio.fixture
async def test_entity(session_maker: async_sessionmaker[AsyncSession]) -> Entity:
    """Create a test entity."""
    async with session_maker() as session:
        entity = Entity(entity_type="test", name="test", description="Test entity", path_id="test/test")
        session.add(entity)
        await session.commit()
        return entity


@pytest.mark.asyncio
async def test_add_observations(observation_service: ObservationService, test_entity: Entity):
    """Test adding observations to an entity."""
    observations = ["Test observation 1", "Test observation 2"]

    result = await observation_service.add_observations(test_entity.id, observations)

    assert len(result) == 2
    assert result[0].content == "Test observation 1"
    assert result[1].content == "Test observation 2"
    assert all(obs.entity_id == test_entity.id for obs in result)


@pytest.mark.asyncio
async def test_search_observations(observation_service: ObservationService, test_entity: Entity):
    """Test searching observations across entities."""
    # First add some observations
    await observation_service.add_observations(
        test_entity.id, ["Unique test content", "Other content"]
    )

    # Search for them
    results = await observation_service.search_observations("unique")

    assert len(results) == 1
    assert results[0].content == "Unique test content"


@pytest.mark.asyncio
async def test_delete_observations(observation_service: ObservationService, test_entity: Entity):
    """Test deleting specific observations from an entity."""
    # First add observations
    await observation_service.add_observations(
        test_entity.id, ["First observation", "Second observation", "Third observation"]
    )

    # Then delete some
    contents_to_delete = ["First observation", "Second observation"]
    result = await observation_service.delete_observations(test_entity.id, contents_to_delete)
    assert result is True

    # Verify through search
    results = await observation_service.search_observations("Third")
    assert len(results) == 1
    assert results[0].content == "Third observation"


@pytest.mark.asyncio
async def test_delete_by_entity(observation_service: ObservationService, test_entity: Entity):
    """Test deleting all observations for an entity."""
    # First add observations
    await observation_service.add_observations(
        test_entity.id, ["First observation", "Second observation"]
    )

    # Delete all observations for entity
    result = await observation_service.delete_by_entity(test_entity.id)
    assert result is True

    # Verify through search
    results = await observation_service.search_observations("observation")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_observation(
    observation_service: ObservationService, test_entity: Entity
):
    """Test deleting observations that don't exist."""
    result = await observation_service.delete_observations(
        test_entity.id, ["Nonexistent observation"]
    )
    assert result is False


@pytest.mark.asyncio
async def test_delete_observations_invalid_entity(observation_service: ObservationService):
    """Test deleting observations for an entity that doesn't exist."""
    result = await observation_service.delete_observations("invalid_entity", ["Test observation"])
    assert result is False


@pytest.mark.asyncio
async def test_observation_with_special_characters(
    observation_service: ObservationService, test_entity: Entity
):
    """Test handling observations with special characters."""
    content = "Test & observation with @#$% special chars!"

    results = await observation_service.add_observations(test_entity.id, [content])
    assert len(results) == 1
    assert results[0].content == content


@pytest.mark.asyncio
async def test_very_long_observation(observation_service: ObservationService, test_entity: Entity):
    """Test handling very long observation content."""
    long_content = "Very long observation " * 100  # ~1800 characters

    results = await observation_service.add_observations(test_entity.id, [long_content])
    assert len(results) == 1
    assert results[0].content == long_content


@pytest.mark.asyncio
async def test_get_observations_by_context(
    observation_service: ObservationService,
    test_entity: Entity,
    session_maker: async_sessionmaker[AsyncSession],
):
    """Test getting observations by context."""
    # Create observation with context
    async with session_maker() as session:
        obs = Observation(
            entity_id=test_entity.id, content="Contextual observation", context="test_context"
        )
        session.add(obs)
        await session.commit()

    results = await observation_service.get_observations_by_context("test_context")

    assert len(results) == 1
    assert results[0].content == "Contextual observation"
    assert results[0].context == "test_context"

"""Additional tests for ObservationService category support."""



@pytest.mark.asyncio
async def test_add_observations_with_categories(
    observation_service: ObservationService,
    test_entity: Entity
):
    """Test adding observations with specific categories."""
    observations = [
        ObservationCreate(content="Tech observation", category=ObservationCategory.TECH),
        ObservationCreate(content="Design observation", category=ObservationCategory.DESIGN),
    ]

    result = await observation_service.add_observations(test_entity.id, observations)

    assert len(result) == 2
    assert result[0].category == ObservationCategory.TECH.value
    assert result[1].category == ObservationCategory.DESIGN.value


@pytest.mark.asyncio
async def test_search_observations_by_category(
    observation_service: ObservationService,
    test_entity: Entity
):
    """Test searching observations with category filter."""
    # Add observations with different categories
    observations = [
        ObservationCreate(content="Tech implementation note", category=ObservationCategory.TECH),
        ObservationCreate(content="Design pattern choice", category=ObservationCategory.DESIGN),
        ObservationCreate(content="Another tech detail", category=ObservationCategory.TECH),
    ]
    await observation_service.add_observations(test_entity.id, observations)

    # Search with category filter
    tech_results = await observation_service.search_observations(
        query="note",
        category=ObservationCategory.TECH
    )
    assert len(tech_results) == 1
    assert tech_results[0].content == "Tech implementation note"

    # Search without category filter
    all_results = await observation_service.search_observations(
        query="tech"
    )
    assert len(all_results) == 2


@pytest.mark.asyncio
async def test_get_observations_by_category(
    observation_service: ObservationService,
    test_entity: Entity
):
    """Test retrieving observations by category."""
    # Add observations with different categories
    observations = [
        ObservationCreate(content="First tech note", category=ObservationCategory.TECH),
        ObservationCreate(content="Design decision", category=ObservationCategory.DESIGN),
        ObservationCreate(content="Second tech note", category=ObservationCategory.TECH),
    ]
    await observation_service.add_observations(test_entity.id, observations)

    # Get tech observations
    tech_obs = await observation_service.get_observations_by_category(ObservationCategory.TECH)
    assert len(tech_obs) == 2
    assert all(obs.category == ObservationCategory.TECH.value for obs in tech_obs)

    # Get observations for unused category
    feature_obs = await observation_service.get_observations_by_category(ObservationCategory.FEATURE)
    assert len(feature_obs) == 0


@pytest.mark.asyncio
async def test_observation_categories(
    observation_service: ObservationService,
    test_entity: Entity
):
    """Test retrieving distinct observation categories."""
    # Add observations with various categories
    observations = [
        ObservationCreate(content="Tech note", category=ObservationCategory.TECH),
        ObservationCreate(content="Design note", category=ObservationCategory.DESIGN),
        ObservationCreate(content="Another tech note", category=ObservationCategory.TECH),
        ObservationCreate(content="Feature note", category=ObservationCategory.FEATURE),
    ]
    await observation_service.add_observations(test_entity.id, observations)

    # Get categories
    categories = await observation_service.observation_categories()
    assert set(categories) == {
        ObservationCategory.TECH.value,
        ObservationCategory.DESIGN.value,
        ObservationCategory.FEATURE.value
    }


@pytest.mark.asyncio
async def test_search_observations_empty_category(
    observation_service: ObservationService,
    test_entity: Entity
):
    """Test search behavior with empty/invalid category."""
    # Add some observations
    observations = [
        ObservationCreate(content="Tech note", category=ObservationCategory.TECH),
    ]
    await observation_service.add_observations(test_entity.id, observations)

    # Search with empty category should return all matches
    results = await observation_service.search_observations(
        query="note",
        category=None
    )
    assert len(results) == 1

    # Search with non-existent category should return empty
    results = await observation_service.search_observations(
        query="note",
        category=ObservationCategory.ISSUE
    )
    assert len(results) == 0


@pytest.mark.asyncio
async def test_default_category_behavior(
    observation_service: ObservationService,
    test_entity: Entity
):
    """Test default category assignment."""
    # Add observation without explicit category
    observations = [
        ObservationCreate(content="Simple note")  # No category specified
    ]
    result = await observation_service.add_observations(test_entity.id, observations)

    assert len(result) == 1
    assert result[0].category == ObservationCategory.NOTE.value  # Should use default