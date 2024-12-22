"""Tests for the EntityRepository."""

from datetime import datetime, UTC

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from basic_memory import db
from basic_memory.models import Entity, Observation, Relation
from basic_memory.repository.entity_repository import EntityRepository


@pytest_asyncio.fixture
async def test_entity(session_maker):
    """Create a test entity."""
    async with db.scoped_session(session_maker) as session:
        entity = Entity(name="test_entity", entity_type="test", description="Test entity")
        session.add(entity)
        return entity


@pytest_asyncio.fixture
async def entity_with_observations(session_maker, test_entity):
    """Create an entity with observations."""
    async with db.scoped_session(session_maker) as session:
        observations = [
            Observation(entity_id=test_entity.id, content="First observation"),
            Observation(entity_id=test_entity.id, content="Second observation"),
        ]
        session.add_all(observations)
        return test_entity


@pytest_asyncio.fixture
async def related_entities(session_maker):
    """Create entities with relations between them."""
    async with db.scoped_session(session_maker) as session:
        source = Entity(
            name="source",
            entity_type="source",
            description="Source entity",
        )
        target = Entity(
            name="target",
            entity_type="target",
            description="Target entity",
        )
        session.add(source)
        session.add(target)
        await session.flush()

        relation = Relation(from_id=source.id, to_id=target.id, relation_type="connects_to")
        session.add(relation)

        return source, target, relation


@pytest.mark.asyncio
async def test_create_entity(entity_repository: EntityRepository):
    """Test creating a new entity"""
    entity_data = {
        "name": "Test",
        "entity_type": "test",
        "description": "Test description",
    }
    entity = await entity_repository.create(entity_data)

    # Verify returned object
    assert entity.id is not None
    assert entity.name == "Test"
    assert entity.description == "Test description"
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)

    # Verify in database
    found = await entity_repository.find_by_id(entity.id)
    assert found is not None
    assert found.id is not None
    assert found.id == entity.id
    assert found.name == entity.name
    assert found.description == entity.description

    # assert relations are eagerly loaded
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0


@pytest.mark.asyncio
async def test_create_all(entity_repository: EntityRepository):
    """Test creating a new entity"""
    entity_data = [
        {
            "name": "Test_1",
            "entity_type": "test",
            "description": "Test description",
        },
        {
            "name": "Test-2",
            "entity_type": "test",
            "description": "Test description",
        },
    ]
    entities = await entity_repository.create_all(entity_data)

    assert len(entities) == 2
    entity = entities[0]

    # Verify in database
    found = await entity_repository.find_by_id(entity.id)
    assert found is not None
    assert found.id is not None
    assert found.id == entity.id
    assert found.name == entity.name
    assert found.description == entity.description

    # assert relations are eagerly loaded
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0


@pytest.mark.asyncio
async def test_entity_type_name_unique_constraint(entity_repository: EntityRepository):
    """Test the unique constraint on entity_type + name combination."""
    # Create first entity
    entity1_data = {
        "name": "Test Entity",
        "entity_type": "type1",
        "description": "First entity",
    }
    await entity_repository.create(entity1_data)

    # Try to create another entity with same type and name
    entity2_data = {
        "name": "Test Entity",  # Same name
        "entity_type": "type1",  # Same type
        "description": "Second entity",
    }

    # Should raise IntegrityError
    with pytest.raises(IntegrityError) as exc_info:
        await entity_repository.create(entity2_data)
    assert "UNIQUE constraint failed: entity.entity_type, entity.name" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_entity_null_description(session_maker, entity_repository: EntityRepository):
    """Test creating an entity with null description"""
    entity_data = {
        "name": "Test",
        "entity_type": "test",
        "description": None,
    }
    entity = await entity_repository.create(entity_data)

    # Verify in database
    async with db.scoped_session(session_maker) as session:
        stmt = select(Entity).where(Entity.id == entity.id)
        result = await session.execute(stmt)
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
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.id == found.id
        assert db_entity.name == found.name
        assert db_entity.description == found.description


@pytest.mark.asyncio
async def test_find_by_type_and_name(entity_repository: EntityRepository, sample_entity: Entity):
    """Test finding an entity by name"""
    found = await entity_repository.get_entity_by_type_and_name(
        sample_entity.entity_type, sample_entity.name
    )
    assert found is not None
    assert found.id == sample_entity.id
    assert found.name == sample_entity.name

    # Verify against direct database query
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.name == sample_entity.name)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.id == found.id
        assert db_entity.name == found.name
        assert db_entity.description == found.description


@pytest.mark.asyncio
async def test_update_entity(entity_repository: EntityRepository, sample_entity: Entity):
    """Test updating an entity"""
    updated = await entity_repository.update(
        sample_entity.id, {"description": "Updated description"}
    )
    assert updated is not None
    assert updated.description == "Updated description"
    assert updated.name == sample_entity.name  # Other fields unchanged

    # Verify in database
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.description == "Updated description"
        assert db_entity.name == sample_entity.name


@pytest.mark.asyncio
async def test_update_entity_to_null(entity_repository: EntityRepository, sample_entity: Entity):
    """Test updating an entity's description to null"""
    updated = await entity_repository.update(sample_entity.id, {"description": None})
    assert updated is not None
    assert updated.description is None

    # Verify in database
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.description is None


@pytest.mark.asyncio
async def test_delete_entity(entity_repository: EntityRepository, test_entity):
    """Test deleting an entity."""
    result = await entity_repository.delete(test_entity.id)
    assert result is True

    # Verify deletion
    deleted = await entity_repository.find_by_id(test_entity.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_entity_with_observations(
    entity_repository: EntityRepository, entity_with_observations
):
    """Test deleting an entity cascades to its observations."""
    entity = entity_with_observations

    result = await entity_repository.delete(entity.id)
    assert result is True

    # Verify entity deletion
    deleted = await entity_repository.find_by_id(entity.id)
    assert deleted is None

    # Verify observations were cascaded
    async with db.scoped_session(entity_repository.session_maker) as session:
        query = select(Observation).filter(Observation.entity_id == entity.id)
        result = await session.execute(query)
        remaining_observations = result.scalars().all()
        assert len(remaining_observations) == 0


@pytest.mark.asyncio
async def test_delete_entities_by_type(entity_repository: EntityRepository, test_entity):
    """Test deleting entities by type."""
    result = await entity_repository.delete_by_fields(entity_type=test_entity.entity_type)
    assert result is True

    # Verify deletion
    async with db.scoped_session(entity_repository.session_maker) as session:
        query = select(Entity).filter(Entity.entity_type == test_entity.entity_type)
        result = await session.execute(query)
        remaining = result.scalars().all()
        assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_entity_with_relations(entity_repository: EntityRepository, related_entities):
    """Test deleting an entity cascades to its relations."""
    source, target, relation = related_entities

    # Delete source entity
    result = await entity_repository.delete(source.id)
    assert result is True

    # Verify relation was cascaded
    async with db.scoped_session(entity_repository.session_maker) as session:
        query = select(Relation).filter(Relation.from_id == source.id)
        result = await session.execute(query)
        remaining_relations = result.scalars().all()
        assert len(remaining_relations) == 0

        # Verify target entity still exists
        target_exists = await entity_repository.find_by_id(target.id)
        assert target_exists is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(entity_repository: EntityRepository):
    """Test deleting an entity that doesn't exist."""
    result = await entity_repository.delete(0)
    assert result is False


@pytest.mark.asyncio
async def test_search(session_maker, entity_repository: EntityRepository):
    """Test searching entities"""
    # First create and commit the entities
    async with db.scoped_session(session_maker) as session:
        entity1 = Entity(
            name="Search Test 1",
            entity_type="test",
            description="First test entity",
        )
        entity2 = Entity(
            name="Search Test 2",
            entity_type="other",
            description="Second test entity",
        )
        session.add_all([entity1, entity2])

    # Then add observations in a new transaction
    async with db.scoped_session(session_maker) as session:
        ts = datetime.now(UTC)
        stmt = text("""
            INSERT INTO observation (entity_id, content, created_at)
            VALUES (:e1_id, :e1_obs, :ts), (:e2_id, :e2_obs, :ts)
        """)
        await session.execute(
            stmt,
            {
                "e1_id": entity1.id,
                "e1_obs": "First observation with searchable content",
                "e2_id": entity2.id,
                "e2_obs": "Another observation to find",
                "ts": ts,
            },
        )

    # Test search by name
    results = await entity_repository.search("Search Test")
    assert len(results) == 2
    names = {e.name for e in results}
    assert "Search Test 1" in names
    assert "Search Test 2" in names

    # Test search by type
    results = await entity_repository.search("other")
    assert len(results) == 1
    assert results[0].entity_type == "other"

    # Test search by observation content
    results = await entity_repository.search("searchable")
    assert len(results) == 1
    assert results[0].id == entity1.id
