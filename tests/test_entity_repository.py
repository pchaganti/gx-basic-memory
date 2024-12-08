"""Tests for EntityRepository."""
import pytest
from datetime import datetime, UTC
from sqlalchemy import text

from basic_memory.models import Entity
from basic_memory.repository.entity_repository import EntityRepository

pytestmark = pytest.mark.asyncio


class TestEntityRepository:
    async def test_create_entity(self, entity_repository: EntityRepository):
        """Test creating a new entity"""
        entity_data = {
            'id': '20240102-test',
            'name': 'Test',
            'entity_type': 'test',
            'description': 'Test description',
            'references': 'Test references'
        }
        entity = await entity_repository.create(entity_data)
        
        assert entity.id == '20240102-test'
        assert entity.name == 'Test'
        assert entity.description == 'Test description'
        assert isinstance(entity.created_at, datetime)
        assert entity.created_at.tzinfo == UTC

    async def test_find_by_id(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test finding an entity by ID"""
        found = await entity_repository.find_by_id(sample_entity.id)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.name == sample_entity.name

    async def test_find_by_name(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test finding an entity by name"""
        found = await entity_repository.find_by_name(sample_entity.name)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.name == sample_entity.name

    async def test_update_entity(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test updating an entity"""
        updated = await entity_repository.update(
            sample_entity.id,
            {'description': 'Updated description'}
        )
        assert updated is not None
        assert updated.description == 'Updated description'
        assert updated.name == sample_entity.name  # Other fields unchanged

    async def test_delete_entity(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test deleting an entity"""
        success = await entity_repository.delete(sample_entity.id)
        assert success is True
        
        # Verify it's gone
        found = await entity_repository.find_by_id(sample_entity.id)
        assert found is None
        
    async def test_search(self, entity_repository: EntityRepository):
        """Test searching entities"""
        # Create test entities with observations
        entity1 = await entity_repository.create({
            'id': '20240102-test1',
            'name': 'Search Test 1',
            'entity_type': 'test',
            'description': 'First test entity'
        })
        
        entity2 = await entity_repository.create({
            'id': '20240102-test2',
            'name': 'Search Test 2',
            'entity_type': 'other',
            'description': 'Second test entity'
        })
        
        # Add observations
        stmt = text("""
            INSERT INTO observation (entity_id, content, created_at)
            VALUES (:e1_id, :e1_obs, :ts), (:e2_id, :e2_obs, :ts)
        """)
        ts = datetime.now(UTC)
        await entity_repository.session.execute(stmt, {
            "e1_id": entity1.id,
            "e1_obs": "First observation with searchable content",
            "e2_id": entity2.id,
            "e2_obs": "Another observation to find",
            "ts": ts
        })
        await entity_repository.session.commit()
        
        # Test search by name
        results = await entity_repository.search('Search Test')
        assert len(results) == 2
        names = {e.name for e in results}
        assert 'Search Test 1' in names
        assert 'Search Test 2' in names
        
        # Test search by type
        results = await entity_repository.search('other')
        assert len(results) == 1
        assert results[0].entity_type == 'other'
        
        # Test search by observation content
        results = await entity_repository.search('searchable')
        assert len(results) == 1
        assert results[0].id == entity1.id