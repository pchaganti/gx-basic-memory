"""Tests for the EntityRepository."""
from datetime import datetime, UTC

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from basic_memory.models import Entity, Observation, Relation
from basic_memory.repository.entity_repository import EntityRepository


@pytest_asyncio.fixture
async def entity_repo(session):
    """Create an EntityRepository with test DB session."""
    return EntityRepository(session)


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
async def entity_with_observations(session, test_entity):
    """Create an entity with observations."""
    observations = [
        Observation(entity_id=test_entity.id, content="First observation"),
        Observation(entity_id=test_entity.id, content="Second observation")
    ]
    session.add_all(observations)
    await session.flush()
    return test_entity


@pytest_asyncio.fixture
async def related_entities(session):
    """Create entities with relations between them."""
    source = Entity(
        id="source/test_entity",
        name="source",
        entity_type="source",
        description="Source entity"
    )
    target = Entity(
        id="target/test_entity",
        name="target",
        entity_type="target",
        description="Target entity"
    )
    session.add_all([source, target])
    await session.flush()

    relation = Relation(
        from_id=source.id,
        to_id=target.id,
        relation_type="connects_to"
    )
    session.add(relation)
    await session.flush()
    
    return source, target, relation

@pytest.mark.asyncio
async def test_create_entity(entity_repository: EntityRepository):
    """Test creating a new entity"""
    entity_data = {
        'name': 'Test',
        'entity_type': 'test',
        'description': 'Test description',
    }
    entity = await entity_repository.create(entity_data)

    # Verify returned object
    assert entity.id == 'test/test'
    assert entity.name == 'Test'
    assert entity.description == 'Test description'
    assert isinstance(entity.created_at, datetime)

    # Verify in database
    stmt = select(Entity).where(Entity.id == entity.id)
    result = await entity_repository.session.execute(stmt)
    db_entity = result.scalar_one()
    assert db_entity.id == entity.id
    assert db_entity.name == entity.name
    assert db_entity.description == entity.description

@pytest.mark.asyncio
async def test_entity_type_name_unique_constraint(entity_repository: EntityRepository):
    """Test the unique constraint on entity_type + name combination."""
    # Create first entity
    entity1_data = {
        'id': '20240102-test1',
        'name': 'Test Entity',
        'entity_type': 'type1',
        'description': 'First entity'
    }
    await entity_repository.create(entity1_data)

    # Try to create another entity with same type and name
    entity2_data = {
        'id': '20240102-test2',
        'name': 'Test Entity',  # Same name
        'entity_type': 'type1',  # Same type
        'description': 'Second entity'
    }

    # Should raise IntegrityError
    with pytest.raises(IntegrityError) as exc_info:
        await entity_repository.create(entity2_data)
    assert 'UNIQUE constraint failed: entity.entity_type, entity.name' in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_entity_null_description(entity_repository: EntityRepository):
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

@pytest.mark.asyncio
async def test_find_by_id(entity_repository: EntityRepository, sample_entity: Entity):
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

@pytest.mark.asyncio
async def test_find_by_name(entity_repository: EntityRepository, sample_entity: Entity):
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

@pytest.mark.asyncio
async def test_update_entity(entity_repository: EntityRepository, sample_entity: Entity):
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

@pytest.mark.asyncio
async def test_update_entity_to_null(entity_repository: EntityRepository, sample_entity: Entity):
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

@pytest.mark.asyncio
async def test_delete_entity_find_by_id(entity_repository: EntityRepository, sample_entity: Entity):
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

@pytest.mark.asyncio
async def test_search(entity_repository: EntityRepository):
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

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_delete_entity(entity_repo, test_entity):
    """Test deleting an entity."""
    result = await entity_repo.delete(test_entity.id)
    assert result is True
    
    # Verify deletion
    deleted = await entity_repo.find_by_id(test_entity.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_entity_with_observations(entity_repo, entity_with_observations):
    """Test deleting an entity cascades to its observations."""
    entity = entity_with_observations
    
    result = await entity_repo.delete(entity.id)
    assert result is True
    
    # Verify entity deletion
    deleted = await entity_repo.find_by_id(entity.id)
    assert deleted is None
    
    # Verify observations were cascaded
    query = select(Observation).filter(Observation.entity_id == entity.id)
    result = await entity_repo.execute_query(query)
    remaining_observations = result.scalars().all()
    assert len(remaining_observations) == 0


@pytest.mark.asyncio
async def test_delete_entities_by_type(entity_repo, test_entity):
    """Test deleting entities by type."""
    result = await entity_repo.delete_by_fields(entity_type=test_entity.entity_type)
    assert result is True
    
    # Verify deletion
    query = select(Entity).filter(Entity.entity_type == test_entity.entity_type)
    result = await entity_repo.execute_query(query)
    remaining = result.scalars().all()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_entity_with_relations(entity_repo, related_entities):
    """Test deleting an entity cascades to its relations."""
    source, target, relation = related_entities
    
    # Delete source entity
    result = await entity_repo.delete(source.id)
    assert result is True
    
    # Verify relation was cascaded
    query = select(Relation).filter(Relation.from_id == source.id)
    result = await entity_repo.execute_query(query)
    remaining_relations = result.scalars().all()
    assert len(remaining_relations) == 0
    
    # Verify target entity still exists
    target_exists = await entity_repo.find_by_id(target.id)
    assert target_exists is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(entity_repo):
    """Test deleting an entity that doesn't exist."""
    result = await entity_repo.delete("nonexistent/id")
    assert result is False