"""Tests for ObservationRepository."""
import pytest
import pytest_asyncio
from basic_memory.models import Entity, Observation
from basic_memory.repository.observation_repository import ObservationRepository

pytestmark = pytest.mark.asyncio


class TestObservationRepository:
    @pytest_asyncio.fixture(scope="function")
    async def sample_observation(self, observation_repository: ObservationRepository, sample_entity: Entity):
        """Create a sample observation for testing"""
        observation_data = {
            'entity_id': sample_entity.id,
            'content': 'Test observation',
            'context': 'test-context'
        }
        return await observation_repository.create(observation_data)

    async def test_create_observation(
        self,
        observation_repository: ObservationRepository,
        sample_entity: Entity
    ):
        """Test creating a new observation"""
        observation_data = {
            'entity_id': sample_entity.id,
            'content': 'Test content',
            'context': 'test-context'
        }
        observation = await observation_repository.create(observation_data)
        
        assert observation.entity_id == sample_entity.id
        assert observation.content == 'Test content'
        assert observation.id is not None  # Should be auto-generated

    async def test_find_by_entity(
        self,
        observation_repository: ObservationRepository,
        sample_observation: Observation,
        sample_entity: Entity
    ):
        """Test finding observations by entity"""
        observations = await observation_repository.find_by_entity(sample_entity.id)
        assert len(observations) == 1
        assert observations[0].id == sample_observation.id
        assert observations[0].content == sample_observation.content

    async def test_find_by_context(
        self,
        observation_repository: ObservationRepository,
        sample_observation: Observation
    ):
        """Test finding observations by context"""
        observations = await observation_repository.find_by_context('test-context')
        assert len(observations) == 1
        assert observations[0].id == sample_observation.id