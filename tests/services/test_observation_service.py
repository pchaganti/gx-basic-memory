"""Tests for the ObservationService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basic_memory.models import Entity, Observation
from basic_memory.schemas.base import ObservationCategory
from basic_memory.schemas.request import ObservationCreate
from basic_memory.services import EntityService
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.observation_service import ObservationService


@pytest.mark.asyncio
async def test_add_observations(observation_service: ObservationService, sample_entity: Entity):
    """Test adding observations to an entity."""
    observations = ["Test observation 1", "Test observation 2"]

    entity = await observation_service.add_observations(sample_entity.path_id, observations)

    observations = entity.observations
    assert len(observations) == 2
    assert observations[0].content == "Test observation 1"
    assert observations[1].content == "Test observation 2"
    assert all(obs.entity_id == sample_entity.id for obs in observations)


@pytest.mark.asyncio
async def test_delete_observations(observation_service: ObservationService, entity_service: EntityService,  sample_entity: Entity):
    """Test deleting specific observations from an entity."""
    # First add observations
    await observation_service.add_observations(
        sample_entity.path_id, ["First observation", "Second observation", "Third observation"]
    )

    # Then delete some
    contents_to_delete = ["First observation", "Second observation"]
    entity = await observation_service.delete_observations(sample_entity.path_id, contents_to_delete)

    # Verify
    entity = await entity_service.get_by_path_id(sample_entity.path_id)
    assert len(entity.observations) == 1
    assert entity.observations[0].content == "Third observation"
    assert entity.observations[0].entity_id == sample_entity.id


@pytest.mark.asyncio
async def test_delete_by_entity(observation_service: ObservationService, sample_entity: Entity):
    """Test deleting all observations for an entity."""
    # First add observations
    await observation_service.add_observations(
        sample_entity.path_id, ["First observation", "Second observation"]
    )

    # Delete all observations for entity
    deleted = await observation_service.delete_by_entity(sample_entity.id)

    # Verify through search
    assert deleted


@pytest.mark.asyncio
async def test_delete_nonexistent_observation(
    observation_service: ObservationService, sample_entity: Entity
):
    """Test deleting observations that don't exist."""
    entity = await observation_service.delete_observations(
        sample_entity.path_id, ["Nonexistent observation"]
    )
    assert entity is not None


@pytest.mark.asyncio
async def test_delete_observations_invalid_entity(observation_service: ObservationService):
    """Test deleting observations for an entity that doesn't exist."""
    
    with pytest.raises(EntityNotFoundError):
        await observation_service.delete_observations("invalid_entity", ["Test observation"])


@pytest.mark.asyncio
async def test_observation_with_special_characters(
    observation_service: ObservationService, sample_entity: Entity
):
    """Test handling observations with special characters."""
    content = "Test & observation with @#$% special chars!"

    entity = await observation_service.add_observations(sample_entity.path_id, [content])
    assert len(entity.observations) == 1
    assert entity.observations[0].content == content


@pytest.mark.asyncio
async def test_very_long_observation(
    observation_service: ObservationService, sample_entity: Entity
):
    """Test handling very long observation content."""
    long_content = "Very long observation " * 100  # ~1800 characters

    entity = await observation_service.add_observations(sample_entity.path_id, [long_content])
    assert len(entity.observations) == 1
    assert entity.observations[0].content == long_content


@pytest.mark.asyncio
async def test_get_observations_by_context(
    observation_service: ObservationService,
    sample_entity: Entity,
    session_maker: async_sessionmaker[AsyncSession],
):
    """Test getting observations by context."""
    # Create observation with context
    async with session_maker() as session:
        obs = Observation(
            entity_id=sample_entity.id, content="Contextual observation", context="test_context"
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
    observation_service: ObservationService, sample_entity: Entity
):
    """Test adding observations with specific categories."""
    observations = [
        ObservationCreate(content="Tech observation", category=ObservationCategory.TECH),
        ObservationCreate(content="Design observation", category=ObservationCategory.DESIGN),
    ]

    entity = await observation_service.add_observations(sample_entity.path_id, observations)

    assert len(entity.observations) == 2
    assert entity.observations[0].category == ObservationCategory.TECH.value
    assert entity.observations[1].category == ObservationCategory.DESIGN.value



@pytest.mark.asyncio
async def test_get_observations_by_category(
    observation_service: ObservationService, sample_entity: Entity
):
    """Test retrieving observations by category."""
    # Add observations with different categories
    observations = [
        ObservationCreate(content="First tech note", category=ObservationCategory.TECH),
        ObservationCreate(content="Design decision", category=ObservationCategory.DESIGN),
        ObservationCreate(content="Second tech note", category=ObservationCategory.TECH),
    ]
    await observation_service.add_observations(sample_entity.path_id, observations)

    # Get tech observations
    tech_obs = await observation_service.get_observations_by_category(ObservationCategory.TECH)
    assert len(tech_obs) == 2
    assert all(obs.category == ObservationCategory.TECH.value for obs in tech_obs)

    # Get observations for unused category
    feature_obs = await observation_service.get_observations_by_category(
        ObservationCategory.FEATURE
    )
    assert len(feature_obs) == 0


@pytest.mark.asyncio
async def test_observation_categories(
    observation_service: ObservationService, sample_entity: Entity
):
    """Test retrieving distinct observation categories."""
    # Add observations with various categories
    observations = [
        ObservationCreate(content="Tech note", category=ObservationCategory.TECH),
        ObservationCreate(content="Design note", category=ObservationCategory.DESIGN),
        ObservationCreate(content="Another tech note", category=ObservationCategory.TECH),
        ObservationCreate(content="Feature note", category=ObservationCategory.FEATURE),
    ]
    await observation_service.add_observations(sample_entity.path_id, observations)

    # Get categories
    categories = await observation_service.observation_categories()
    assert set(categories) == {
        ObservationCategory.TECH.value,
        ObservationCategory.DESIGN.value,
        ObservationCategory.FEATURE.value,
    }


@pytest.mark.asyncio
async def test_default_category_behavior(
    observation_service: ObservationService, sample_entity: Entity
):
    """Test default category assignment."""
    # Add observation without explicit category
    observations = [
        ObservationCreate(content="Simple note")  # No category specified
    ]
    entity = await observation_service.add_observations(sample_entity.path_id, observations)

    assert len(entity.observations) == 1
    assert entity.observations[0].category == ObservationCategory.NOTE.value  # Should use default
