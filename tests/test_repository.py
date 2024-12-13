"""Tests for base repository functionality."""
import pytest
from sqlalchemy import select

from basic_memory.models import Base, Observation
from basic_memory.repository import Repository

pytestmark = pytest.mark.anyio


async def test_create_with_defaults(session):
    """Test creating an entity with default timestamps."""
    repo = Repository(session, Observation)
    
    # Create observation without timestamps
    observation_data = {
        'entity_id': 'test/test_entity',
        'content': 'Test observation'
    }
    
    # Should succeed even though created_at not provided
    observation = await repo.create(observation_data)
    assert observation.id is not None
    assert observation.content == 'Test observation'
    assert observation.created_at is not None  # Should have default value
    
    # Verify in database
    stmt = select(Observation).where(Observation.id == observation.id)
    result = await session.execute(stmt)
    db_observation = result.scalar_one()
    assert db_observation.created_at is not None