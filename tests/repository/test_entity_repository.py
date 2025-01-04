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
async def entity_with_observations(session_maker, sample_entity):
    """Create an entity with observations."""
    async with db.scoped_session(session_maker) as session:
        observations = [
            Observation(entity_id=sample_entity.id, content="First observation"),
            Observation(entity_id=sample_entity.id, content="Second observation"),
        ]
        session.add_all(observations)
        return sample_entity


@pytest_asyncio.fixture
async def related_entities(session_maker):
    """Create entities with relations between them."""
    async with db.scoped_session(session_maker) as session:
        source = Entity(
            name="source",
            entity_type="source",
            path_id="source/source",
            file_path="source/source.md",
            description="Source entity",
        )
        target = Entity(
            name="target",
            entity_type="target",
            path_id="target/target",
            file_path="target/target.md",
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
        "path_id": "test/test",
        "file_path": "test/test.md",
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
            "path_id": "test/test_1",
            "file_path": "test/test_1.md",
            "description": "Test description",
        },
        {
            "name": "Test-2",
            "entity_type": "test",
            "path_id": "test/test_2",
            "file_path": "test/test_2.md",
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
        "path_id": "type1/test_entity",
        "file_path": "type1/test_entity1.md", 
        "description": "First entity",
    }
    await entity_repository.create(entity1_data)

    # Try to create another entity with same type and name
    entity2_data = {
        "name": "Test Entity",  # Same name
        "entity_type": "type1",  # Same type
        "path_id": "type1/test_entity",
        "file_path": "type1/test_entity2.md",
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
        "path_id": "test/test",
        "file_path": "test/test.md",
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
async def test_delete_entity(entity_repository: EntityRepository, sample_entity):
    """Test deleting an entity."""
    result = await entity_repository.delete(sample_entity.id)
    assert result is True

    # Verify deletion
    deleted = await entity_repository.find_by_id(sample_entity.id)
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
async def test_delete_entities_by_type(entity_repository: EntityRepository, sample_entity):
    """Test deleting entities by type."""
    result = await entity_repository.delete_by_fields(entity_type=sample_entity.entity_type)
    assert result is True

    # Verify deletion
    async with db.scoped_session(entity_repository.session_maker) as session:
        query = select(Entity).filter(Entity.entity_type == sample_entity.entity_type)
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
            path_id="test/search_test_1",
            file_path="test/search_test_1.md",
            description="First test entity",
        )
        entity2 = Entity(
            name="Search Test 2",
            entity_type="other",
            path_id="other/search_test_2",
            file_path="other/search_test_2.md",
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


@pytest_asyncio.fixture
async def test_entities(session_maker):
    """Create multiple test entities."""
    async with db.scoped_session(session_maker) as session:
        entities = [
            Entity(
                name="entity1",
                entity_type="type1",
                description="First test entity",
                path_id="type1/entity1",
                file_path="type1/entity1.md",
            ),
            Entity(
                name="entity2",
                entity_type="type1",
                description="Second test entity",
                path_id="type1/entity2",
                file_path="type1/entity2.md",
            ),
            Entity(
                name="entity3",
                entity_type="type2",
                description="Third test entity",
                path_id="type2/entity3",
                file_path="type2/entity3.md",
            ),
        ]
        session.add_all(entities)
        return entities


@pytest.mark.asyncio
async def test_find_by_path_ids(entity_repository: EntityRepository, test_entities):
    """Test finding multiple entities by their type/name pairs."""
    # Test finding multiple entities
    path_ids = [e.path_id for e in test_entities]
    found = await entity_repository.find_by_path_ids(path_ids)
    assert len(found) == 3
    names = {e.name for e in found}
    assert names == {"entity1", "entity2", "entity3"}

    # Test finding subset of entities
    path_ids = [e.path_id for e in test_entities if e.name != "entity2"]
    found = await entity_repository.find_by_path_ids(path_ids)
    assert len(found) == 2
    names = {e.name for e in found}
    assert names == {"entity1", "entity3"}

    # Test with non-existent entities
    path_ids = ["type1/entity1", "type3/nonexistent"]
    found = await entity_repository.find_by_path_ids(path_ids)
    assert len(found) == 1
    assert found[0].name == "entity1"

    # Test empty input
    found = await entity_repository.find_by_path_ids([])
    assert len(found) == 0


@pytest.mark.asyncio
async def test_delete_by_path_ids(entity_repository: EntityRepository, test_entities):
    """Test deleting entities by type/name pairs."""
    # Test deleting multiple entities
    path_ids = [e.path_id for e in test_entities if e.name != "entity3"]
    deleted_count = await entity_repository.delete_by_path_ids(path_ids)
    assert deleted_count == 2

    # Verify deletions
    remaining = await entity_repository.find_all()
    assert len(remaining) == 1
    assert remaining[0].name == "entity3"

    # Test deleting non-existent entities
    path__ids = ["type3/nonexistent"]
    deleted_count = await entity_repository.delete_by_path_ids(path__ids)
    assert deleted_count == 0

    # Test empty input
    deleted_count = await entity_repository.delete_by_path_ids([])
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_delete_by_path_ids_with_observations(
    entity_repository: EntityRepository, test_entities, session_maker
):
    """Test deleting entities with observations by type/name pairs."""
    # Add observations
    async with db.scoped_session(session_maker) as session:
        observations = [
            Observation(entity_id=test_entities[0].id, content="First observation"),
            Observation(entity_id=test_entities[1].id, content="Second observation"),
        ]
        session.add_all(observations)

    # Delete entities
    path_ids = [e.path_id for e in test_entities]
    deleted_count = await entity_repository.delete_by_path_ids(path_ids)
    assert deleted_count == 3

    # Verify observations were cascaded
    async with db.scoped_session(session_maker) as session:
        query = select(Observation).filter(
            Observation.entity_id.in_([e.id for e in test_entities[:2]])
        )
        result = await session.execute(query)
        remaining_observations = result.scalars().all()
        assert len(remaining_observations) == 0


@pytest.mark.asyncio
async def test_list_entities_with_related(entity_repository: EntityRepository, session_maker):
    """Test listing entities with related entities included."""
    
    # Create test entities
    async with db.scoped_session(session_maker) as session:
        # Core entities
        core = Entity(
            name="core_service",
            entity_type="service",
            path_id="service/core",
            file_path="service/core.md",
            description="Core service"
        )
        dbe = Entity(
            name="db_service",
            entity_type="service",
            path_id="service/db",
            file_path="service/db.md",
            description="Database service"
        )
        # Related entity of different type
        config = Entity(
            name="service_config",
            entity_type="configuration",
            path_id="config/service",
            file_path="config/service.md",
            description="Service configuration"
        )
        session.add_all([core, dbe, config])
        await session.flush()

        # Create relations in both directions
        relations = [
            # core -> db (depends_on)
            Relation(from_id=core.id, to_id=dbe.id, relation_type="depends_on"),
            # config -> core (configures)
            Relation(from_id=config.id, to_id=core.id, relation_type="configures")
        ]
        session.add_all(relations)

    # Test 1: List services without related entities
    services = await entity_repository.list_entities(
        entity_type="service",
        include_related=False
    )
    assert len(services) == 2
    service_names = {s.name for s in services}
    assert service_names == {"core_service", "db_service"}

    # Test 2: List services with related entities
    services_and_related = await entity_repository.list_entities(
        entity_type="service",
        include_related=True
    )
    assert len(services_and_related) == 3
    # Should include both services and the config
    entity_names = {e.name for e in services_and_related}
    assert entity_names == {"core_service", "db_service", "service_config"}

    # Test 3: Verify relations are loaded
    core_service = next(e for e in services_and_related if e.name == "core_service")
    assert len(core_service.outgoing_relations) > 0  # Has incoming relation from config
    assert len(core_service.incoming_relations) > 0    # Has outgoing relation to db

    # Test 4: List configurations with related
    configs = await entity_repository.list_entities(
        entity_type="configuration",
        include_related=True,
        sort_by="name"
    )
    config_names = {c.name for c in configs}
    # Should include both config and the services it relates to
    assert "service_config" in config_names
    assert "core_service" in config_names  # Related via configures relation