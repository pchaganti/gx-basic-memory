"""Tests for the ObservationService."""
import pytest
import pytest_asyncio
from pathlib import Path

from basic_memory.models import Entity, Observation
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.services.observation_service import ObservationService
from basic_memory.services import DatabaseSyncError


@pytest_asyncio.fixture
async def observation_service(session):
    """Create a test ObservationService."""
    repo = ObservationRepository(session)
    return ObservationService(Path("/test"), repo)


@pytest_asyncio.fixture
async def test_entity(session):
    """Create a test entity."""
    entity = Entity(
        id="test/test_entity",
        name="test_entity",
        entity_type="test",
        description="Test entity"
    )
    session.add(entity)
    await session.flush()
    return entity


@pytest_asyncio.fixture
async def test_observations(session, test_entity):
    """Create test observations."""
    observations = [
        Observation(entity_id=test_entity.id, content="First observation"),
        Observation(entity_id=test_entity.id, content="Second observation"),
        Observation(entity_id=test_entity.id, content="Third observation")
    ]
    session.add_all(observations)
    await session.flush()
    return observations


@pytest.mark.asyncio
async def test_add_observations(observation_service, test_entity):
    """Test adding observations to an entity."""
    observations = ["Test observation 1", "Test observation 2"]
    
    result = await observation_service.add_observations(test_entity.id, observations)
    
    assert len(result) == 2
    assert result[0].content == "Test observation 1"
    assert result[1].content == "Test observation 2"
    assert all(obs.entity_id == test_entity.id for obs in result)


@pytest.mark.asyncio
async def test_delete_observations(observation_service, test_entity, test_observations):
    """Test deleting specific observations from an entity."""
    contents_to_delete = ["First observation", "Second observation"]
    
    result = await observation_service.delete_observations(test_entity.id, contents_to_delete)
    
    assert result is True
    
    # Verify observations were deleted
    remaining = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(remaining) == 1
    assert remaining[0].content == "Third observation"


@pytest.mark.asyncio
async def test_delete_by_entity(observation_service, test_entity, test_observations):
    """Test deleting all observations for an entity."""
    result = await observation_service.delete_by_entity(test_entity.id)
    
    assert result is True
    
    # Verify all observations were deleted
    remaining = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_observation(observation_service, test_entity):
    """Test deleting observations that don't exist."""
    result = await observation_service.delete_observations(test_entity.id, ["Nonexistent observation"])
    
    assert result is False


@pytest.mark.asyncio
async def test_delete_observations_invalid_entity(observation_service):
    """Test deleting observations for an entity that doesn't exist."""
    result = await observation_service.delete_observations("invalid_entity", ["Test observation"])
    
    # Should return False since there were no observations to delete
    assert result is False


@pytest.mark.asyncio
async def test_search_observations(observation_service, test_observations):
    """Test searching observations."""
    results = await observation_service.search_observations("First")
    
    assert len(results) == 1
    assert results[0].content == "First observation"


@pytest.mark.asyncio
async def test_get_observations_by_context(observation_service, session, test_entity):
    """Test getting observations by context."""
    obs = Observation(
        entity_id=test_entity.id,
        content="Contextual observation",
        context="test_context"
    )
    session.add(obs)
    await session.flush()
    
    results = await observation_service.get_observations_by_context("test_context")
    
    assert len(results) == 1
    assert results[0].content == "Contextual observation"
    assert results[0].context == "test_context"