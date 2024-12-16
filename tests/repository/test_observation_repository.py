"""Tests for the ObservationRepository."""

import pytest
import pytest_asyncio
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory.models import Entity, Observation
from basic_memory.repository.observation_repository import ObservationRepository


@pytest_asyncio.fixture(scope="function")
async def repo(observation_repository):
    """Create an ObservationRepository instance"""
    return observation_repository


@pytest_asyncio.fixture(scope="function")
async def sample_observation(repo, sample_entity: Entity):
    """Create a sample observation for testing"""
    observation_data = {
        "entity_id": sample_entity.id,
        "content": "Test observation",
        "context": "test-context",
    }
    return await repo.create(observation_data)


@pytest.mark.asyncio
async def test_create_observation(
    observation_repository: ObservationRepository, sample_entity: Entity
):
    """Test creating a new observation"""
    observation_data = {
        "entity_id": sample_entity.id,
        "content": "Test content",
        "context": "test-context",
    }
    observation = await observation_repository.create(observation_data)

    assert observation.entity_id == sample_entity.id
    assert observation.content == "Test content"
    assert observation.id is not None  # Should be auto-generated


@pytest.mark.asyncio
async def test_create_observation_entity_does_not_exist(
    observation_repository: ObservationRepository, sample_entity: Entity
):
    """Test creating a new observation"""
    observation_data = {
        "entity_id": "does-not-exist",
        "content": "Test content",
        "context": "test-context",
    }
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        await observation_repository.create(observation_data)


@pytest.mark.asyncio
async def test_find_by_entity(
    observation_repository: ObservationRepository,
    sample_observation: Observation,
    sample_entity: Entity,
):
    """Test finding observations by entity"""
    observations = await observation_repository.find_by_entity(sample_entity.id)
    assert len(observations) == 1
    assert observations[0].id == sample_observation.id
    assert observations[0].content == sample_observation.content


@pytest.mark.asyncio
async def test_find_by_context(
    observation_repository: ObservationRepository, sample_observation: Observation
):
    """Test finding observations by context"""
    observations = await observation_repository.find_by_context("test-context")
    assert len(observations) == 1
    assert observations[0].id == sample_observation.id
    assert observations[0].content == sample_observation.content


@pytest.mark.asyncio
async def test_delete_observations(session: AsyncSession, repo):
    """Test deleting observations by entity_id."""
    # Create test entity
    entity = Entity(
        id="test/test_entity", name="test_entity", entity_type="test", description="Test entity"
    )
    session.add(entity)
    await session.flush()

    # Create test observations
    obs1 = Observation(entity_id=entity.id, content="Test observation 1")
    obs2 = Observation(entity_id=entity.id, content="Test observation 2")
    session.add_all([obs1, obs2])
    await session.flush()

    # Test deletion by entity_id
    deleted = await repo.delete_by_fields(entity_id=entity.id)
    assert deleted is True

    # Verify observations were deleted
    remaining = await repo.find_by_entity(entity.id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_observation_by_id(session: AsyncSession, repo):
    """Test deleting a single observation by its ID."""
    # Create test entity
    entity = Entity(
        id="test/test_entity", name="test_entity", entity_type="test", description="Test entity"
    )
    session.add(entity)
    await session.flush()

    # Create test observation
    obs = Observation(entity_id=entity.id, content="Test observation")
    session.add(obs)
    await session.flush()

    # Test deletion by ID
    deleted = await repo.delete(obs.id)
    assert deleted is True

    # Verify observation was deleted
    remaining = await repo.find_by_id(obs.id)
    assert remaining is None


@pytest.mark.asyncio
async def test_delete_observation_by_content(session: AsyncSession, repo):
    """Test deleting observations by content."""
    # Create test entity
    entity = Entity(
        id="test/test_entity", name="test_entity", entity_type="test", description="Test entity"
    )
    session.add(entity)
    await session.flush()

    # Create test observations
    obs1 = Observation(entity_id=entity.id, content="Delete this observation")
    obs2 = Observation(entity_id=entity.id, content="Keep this observation")
    session.add_all([obs1, obs2])
    await session.flush()

    # Test deletion by content
    deleted = await repo.delete_by_fields(content="Delete this observation")
    assert deleted is True

    # Verify only matching observation was deleted
    remaining = await repo.find_by_entity(entity.id)
    assert len(remaining) == 1
    assert remaining[0].content == "Keep this observation"
