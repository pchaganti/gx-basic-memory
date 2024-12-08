"""Tests for ObservationService."""
import pytest

from basic_memory.models import Observation
from basic_memory.schemas import EntityIn, ObservationIn

pytestmark = pytest.mark.asyncio


async def test_add_observation_success(observation_service, test_entity):
    """Test successful observation addition."""
    observation_data = ObservationIn(
        content="New observation",
        context="test-context"
    )
    
    entity_data = EntityIn(
        name=test_entity.name,
        entity_type=test_entity.entity_type,
        id=test_entity.id,
        observations=[]
    )
    
    # Act
    observations = await observation_service.add_observations(entity_data, [observation_data])
    
    # Assert
    assert len(observations) == 1
    assert isinstance(observations[0], Observation)
    assert observations[0].content == "New observation"

    # Verify database index
    db_observations = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(db_observations) == 1
    assert any(obs.content == "New observation" and obs.context == "test-context"
              for obs in db_observations)



async def test_search_observations(observation_service, test_entity):
    """Test searching observations across entities."""
    # Arrange
    entity_data = EntityIn(
        name=test_entity.name,
        entity_type=test_entity.entity_type,
        id=test_entity.id,
        observations=[]
    )
    
    await observation_service.add_observations(
        entity_data,
        [ObservationIn(content="Unique test content"), ObservationIn(content="Other content")]
    )

    # Act
    results = await observation_service.search_observations("unique")
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "Unique test content"


async def test_get_observations_by_context(observation_service, test_entity):
    """Test retrieving observations by context."""
    # Arrange
    entity_data = EntityIn(
        name=test_entity.name,
        entity_type=test_entity.entity_type,
        id=test_entity.id,
        observations=[]
    )
    
    await observation_service.add_observations(
        entity_data,
        [ObservationIn(content="Context observation", context="test-context"),
         ObservationIn(content="Other observation", context="other-context")]
    )

    # Act
    results = await observation_service.get_observations_by_context("test-context")
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "Context observation"


# Edge Cases

async def test_observation_with_special_characters(observation_service, test_entity):
    """Test handling observations with special characters."""
    content = "Test & observation with @#$% special chars!"
    entity_data = EntityIn(
        name=test_entity.name,
        entity_type=test_entity.entity_type,
        id=test_entity.id,
    )

    observations = await observation_service.add_observations(entity_data, [ObservationIn(content=content)])
    assert observations[0].content == content


async def test_very_long_observation(observation_service, test_entity):
    """Test handling very long observation content."""
    long_content = "Very long observation " * 100  # ~1800 characters
    entity_data = EntityIn(
        name=test_entity.name,
        entity_type=test_entity.entity_type,
        id=test_entity.id,
        observations=[]
    )

    observations = await observation_service.add_observations(entity_data, [ObservationIn(content=long_content)])
    assert observations[0].content == long_content
    