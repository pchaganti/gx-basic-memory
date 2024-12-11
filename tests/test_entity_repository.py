"""Tests for EntityRepository."""
import pytest
from datetime import datetime, UTC
from sqlalchemy import text, select

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
        }
        entity = await entity_repository.create(entity_data)
        
        # Verify returned object
        assert entity.id == '20240102-test'
        assert entity.name == 'Test'
        assert entity.description == 'Test description'
        assert isinstance(entity.created_at, datetime)
        assert entity.created_at.tzinfo == UTC

        # Verify in database
        stmt = select(Entity).where(Entity.id == entity.id)
        result = await entity_repository.session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.id == entity.id
        assert db_entity.name == entity.name
        assert db_entity.description == entity.description

    async def test_create_entity_null_description(self, entity_repository: EntityRepository):
        """Test creating an entity with null description"""
        entity_data = {
            'id': '20240102-test',
            'name': 'Test',
            'entity_type': 'test',
            'description': None,
        }
        entity = await entity_repository.create(entity_data)
        
        # Verify in database
        stmt = select(Entity).where(Entity.id == entity.id)
        result = await entity_repository.session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.description is None

    async def test_find_by_id(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test finding an entity by ID"""
        found = await entity_repository.find_by_id(sample_entity.id)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.name == sample_entity.name

        # Verify against direct database query
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await entity_repository.session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.id == found.id
        assert db_entity.name == found.name
        assert db_entity.description == found.description

    async def test_find_by_name(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test finding an entity by name"""
        found = await entity_repository.find_by_name(sample_entity.name)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.name == sample_entity.name

        # Verify against direct database query
        stmt = select(Entity).where(Entity.name == sample_entity.name)
        result = await entity_repository.session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.id == found.id
        assert db_entity.name == found.name
        assert db_entity.description == found.description

    async def test_update_entity(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test updating an entity"""
        updated = await entity_repository.update(
            sample_entity.id,
            {'description': 'Updated description'}
        )
        assert updated is not None
        assert updated.description == 'Updated description'
        assert updated.name == sample_entity.name  # Other fields unchanged

        # Verify in database
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await entity_repository.session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.description == 'Updated description'
        assert db_entity.name == sample_entity.name

    async def test_update_entity_to_null(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test updating an entity's description to null"""
        updated = await entity_repository.update(
            sample_entity.id,
            {'description': None}
        )
        assert updated is not None
        assert updated.description is None

        # Verify in database
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await entity_repository.session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.description is None

    async def test_delete_entity(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test deleting an entity"""
        success = await entity_repository.delete(sample_entity.id)
        assert success is True
        
        # Verify it's gone
        found = await entity_repository.find_by_id(sample_entity.id)
        assert found is None

        # Verify with direct query
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await entity_repository.session.execute(stmt)
        assert result.first() is None
        
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
        
        # Verify entities in database
        stmt = select(Entity).where(Entity.id.in_([entity1.id, entity2.id]))
        result = await entity_repository.session.execute(stmt)
        db_entities = result.scalars().all()
        assert len(db_entities) == 2
        
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


async def test_find_by_type_and_name(entity_repository: EntityRepository):
    """Test finding an entity by type and name combination."""
    # Create two entities with same name but different types
    entity1 = await entity_repository.create({
        'id': '20240102-test1',
        'name': 'Test Entity',
        'entity_type': 'type1',
        'description': 'First test entity'
    })

    entity2 = await entity_repository.create({
        'id': '20240102-test2',
        'name': 'Test Entity',
        'entity_type': 'type2',
        'description': 'Second test entity'
    })

    # Should find correct entity when both type and name match
    found = await entity_repository.find_by_type_and_name('type1', 'Test Entity')
    assert found is not None
    assert found.id == entity1.id
    assert found.entity_type == 'type1'
    assert found.name == 'Test Entity'

    # Should find other entity with same name but different type
    found = await entity_repository.find_by_type_and_name('type2', 'Test Entity')
    assert found is not None
    assert found.id == entity2.id
    assert found.entity_type == 'type2'
    assert found.name == 'Test Entity'

    # Should return None when type doesn't match
    found = await entity_repository.find_by_type_and_name('nonexistent', 'Test Entity')
    assert found is None

    # Should return None when name doesn't match
    found = await entity_repository.find_by_type_and_name('type1', 'Nonexistent')
    assert found is None

    # Verify relationships are loaded
    entity3 = await entity_repository.create({
        'id': '20240102-test3',
        'name': 'Entity With Relations',
        'entity_type': 'type3',
        'description': 'Entity with observations and relations'
    })

    # Add an observation
    stmt = text("""
        INSERT INTO observation (entity_id, content, created_at)
        VALUES (:entity_id, :content, :ts)
    """)
    ts = datetime.now(UTC)
    await entity_repository.session.execute(stmt, {
        "entity_id": entity3.id,
        "content": "Test observation",
        "ts": ts
    })
    await entity_repository.session.commit()

    # Find entity and verify relationships are loaded
    found = await entity_repository.find_by_type_and_name('type3', 'Entity With Relations')
    assert found is not None
    assert len(found.observations) == 1
    assert found.observations[0].content == "Test observation"