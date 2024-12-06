"""Tests for ObservationService."""
import pytest
import pytest_asyncio
from sqlalchemy import delete

from basic_memory.models import Observation as DbObservation
from basic_memory.repository import ObservationRepository
from basic_memory.services import (
    EntityService, ObservationService,
    ServiceError, DatabaseSyncError
)
from basic_memory.schemas import Entity, Observation
from basic_memory.fileio import read_entity_file, FileOperationError

pytestmark = pytest.mark.asyncio


async def test_add_observation_success(observation_service, test_entity):
    """Test successful observation addition."""
    # Act
    observation = await observation_service.add_observation(
        entity=test_entity,
        content="New observation",
        context="test-context"
    )
    
    # Assert
    assert isinstance(observation, Observation)
    assert observation.content == "New observation"
    
    # Verify file update
    entity = await read_entity_file(observation_service.entities_path, test_entity.id)
    assert len(entity.observations) == 1
    assert any(obs.content == "New observation" for obs in entity.observations)
    
    # Verify database index
    db_observations = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(db_observations) == 1
    assert any(obs.content == "New observation" and obs.context == "test-context"
              for obs in db_observations)


async def test_file_operation_error(observation_service, test_entity, mocker):
    """Test handling of file operation errors."""
    async def mock_write(*args, **kwargs):
        print("Mock write called with:", args, kwargs)
        raise FileOperationError("Mock file error")
    
    mocker.patch('basic_memory.services.observation_service.write_entity_file', mock_write)
    
    with pytest.raises(FileOperationError):
        await observation_service.add_observation(
            test_entity,
            "Test observation"
        )


async def test_search_observations(observation_service, test_entity):
    """Test searching observations across entities."""
    # Arrange
    await observation_service.add_observation(test_entity, "Unique test content")
    await observation_service.add_observation(test_entity, "Other content")
    
    # Act
    results = await observation_service.search_observations("unique")
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "Unique test content"


async def test_get_observations_by_context(observation_service, test_entity):
    """Test retrieving observations by context."""
    # Arrange
    await observation_service.add_observation(
        test_entity,
        "Context observation",
        context="test-context"
    )
    await observation_service.add_observation(
        test_entity,
        "Other observation",
        context="other-context"
    )
    
    # Act
    results = await observation_service.get_observations_by_context("test-context")
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "Context observation"


async def test_rebuild_observation_index(observation_service, test_entity):
    """Test rebuilding observation index from filesystem."""
    # Arrange - Add observations and clear database
    await observation_service.add_observation(test_entity, "Test observation 1")
    await observation_service.add_observation(test_entity, "Test observation 2")
    
    # Clear database but keep files
    await observation_service.observation_repo.execute_query(delete(DbObservation))
    
    # Act
    await observation_service.rebuild_observation_index()
    
    # Assert
    db_observations = await observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(db_observations) == 2
    observation_contents = {obs.content for obs in db_observations}
    assert observation_contents == {
        "Test observation 1",
        "Test observation 2"
    }


# Edge Cases

async def test_observation_with_special_characters(observation_service, test_entity):
    """Test handling observations with special characters."""
    content = "Test & observation with @#$% special chars!"
    observation = await observation_service.add_observation(
        test_entity,
        content
    )
    assert observation.content == content
    
    # Verify file content
    entity = await read_entity_file(observation_service.entities_path, test_entity.id)
    assert any(obs.content == content for obs in entity.observations)


async def test_very_long_observation(observation_service, test_entity):
    """Test handling very long observation content."""
    long_content = "Very long observation " * 100  # ~1800 characters
    observation = await observation_service.add_observation(
        test_entity,
        long_content
    )
    assert observation.content == long_content
    
    # Verify file content
    entity = await read_entity_file(observation_service.entities_path, test_entity.id)
    assert any(obs.content.rstrip() == long_content.rstrip() for obs in entity.observations)