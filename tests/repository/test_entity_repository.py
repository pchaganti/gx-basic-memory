"""Tests for the EntityRepository."""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

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
            title="source",
            entity_type="test",
            path_id="source/source",
            file_path="source/source.md",
            summary="Source entity",
            content_type="text/markdown",
        )
        target = Entity(
            title="target",
            entity_type="test",
            path_id="target/target",
            file_path="target/target.md",
            summary="Target entity",
            content_type="text/markdown",
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
        "title": "Test",
        "entity_type": "test",
        "path_id": "test/test",
        "file_path": "test/test.md",
        "summary": "Test description",
        "content_type": "text/markdown",
    }
    entity = await entity_repository.create(entity_data)

    # Verify returned object
    assert entity.id is not None
    assert entity.title == "Test"
    assert entity.summary == "Test description"
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)

    # Verify in database
    found = await entity_repository.find_by_id(entity.id)
    assert found is not None
    assert found.id is not None
    assert found.id == entity.id
    assert found.title == entity.title
    assert found.summary == entity.summary

    # assert relations are eagerly loaded
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0


@pytest.mark.asyncio
async def test_create_all(entity_repository: EntityRepository):
    """Test creating a new entity"""
    entity_data = [
        {
            "title": "Test_1",
            "entity_type": "test",
            "path_id": "test/test_1",
            "file_path": "test/test_1.md",
            "summary": "Test description",
            "content_type": "text/markdown",
        },
        {
            "title": "Test-2",
            "entity_type": "test",
            "path_id": "test/test_2",
            "file_path": "test/test_2.md",
            "summary": "Test description",
            "content_type": "text/markdown",
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
    assert found.title == entity.title
    assert found.summary == entity.summary

    # assert relations are eagerly loaded
    assert len(entity.observations) == 0
    assert len(entity.relations) == 0


@pytest.mark.asyncio
async def test_create_entity_null_description(session_maker, entity_repository: EntityRepository):
    """Test creating an entity with null description"""
    entity_data = {
        "title": "Test",
        "entity_type": "test",
        "path_id": "test/test",
        "file_path": "test/test.md",
        "content_type": "text/markdown",
        "summary": None,
    }
    entity = await entity_repository.create(entity_data)

    # Verify in database
    async with db.scoped_session(session_maker) as session:
        stmt = select(Entity).where(Entity.id == entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.summary is None


@pytest.mark.asyncio
async def test_find_by_id(entity_repository: EntityRepository, sample_entity: Entity):
    """Test finding an entity by ID"""
    found = await entity_repository.find_by_id(sample_entity.id)
    assert found is not None
    assert found.id == sample_entity.id
    assert found.title == sample_entity.title

    # Verify against direct database query
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.id == found.id
        assert db_entity.title == found.title
        assert db_entity.summary == found.summary


@pytest.mark.asyncio
async def test_update_entity(entity_repository: EntityRepository, sample_entity: Entity):
    """Test updating an entity"""
    updated = await entity_repository.update(
        sample_entity.id, {"summary": "Updated description"}
    )
    assert updated is not None
    assert updated.summary == "Updated description"
    assert updated.title == sample_entity.title  # Other fields unchanged

    # Verify in database
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.summary == "Updated description"
        assert db_entity.title == sample_entity.title


@pytest.mark.asyncio
async def test_update_entity_to_null(entity_repository: EntityRepository, sample_entity: Entity):
    """Test updating an entity's description to null"""
    updated = await entity_repository.update(sample_entity.id, {"summary": None})
    assert updated is not None
    assert updated.summary is None

    # Verify in database
    async with db.scoped_session(entity_repository.session_maker) as session:
        stmt = select(Entity).where(Entity.id == sample_entity.id)
        result = await session.execute(stmt)
        db_entity = result.scalar_one()
        assert db_entity.summary is None


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


@pytest_asyncio.fixture
async def test_entities(session_maker):
    """Create multiple test entities."""
    async with db.scoped_session(session_maker) as session:
        entities = [
            Entity(
                title="entity1",
                entity_type="test",
                summary="First test entity",
                path_id="type1/entity1",
                file_path="type1/entity1.md",
                content_type= "text/markdown",
            ),
            Entity(
                title="entity2",
                entity_type="test",
                summary="Second test entity",
                path_id="type1/entity2",
                file_path="type1/entity2.md",
                content_type="text/markdown",
            ),
            Entity(
                title="entity3",
                entity_type="test",
                summary="Third test entity",
                path_id="type2/entity3",
                file_path="type2/entity3.md",
                content_type="text/markdown",
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
    names = {e.title for e in found}
    assert names == {"entity1", "entity2", "entity3"}

    # Test finding subset of entities
    path_ids = [e.path_id for e in test_entities if e.title != "entity2"]
    found = await entity_repository.find_by_path_ids(path_ids)
    assert len(found) == 2
    names = {e.title for e in found}
    assert names == {"entity1", "entity3"}

    # Test with non-existent entities
    path_ids = ["type1/entity1", "type3/nonexistent"]
    found = await entity_repository.find_by_path_ids(path_ids)
    assert len(found) == 1
    assert found[0].title == "entity1"

    # Test empty input
    found = await entity_repository.find_by_path_ids([])
    assert len(found) == 0


@pytest.mark.asyncio
async def test_delete_by_path_ids(entity_repository: EntityRepository, test_entities):
    """Test deleting entities by type/name pairs."""
    # Test deleting multiple entities
    path_ids = [e.path_id for e in test_entities if e.title != "entity3"]
    deleted_count = await entity_repository.delete_by_path_ids(path_ids)
    assert deleted_count == 2

    # Verify deletions
    remaining = await entity_repository.find_all()
    assert len(remaining) == 1
    assert remaining[0].title == "entity3"

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
            title="core_service",
            entity_type="note",
            path_id="service/core",
            file_path="service/core.md",
            summary="Core service",
            content_type="text/markdown",
        )
        dbe = Entity(
            title="db_service",
            entity_type="test",
            path_id="service/db",
            file_path="service/db.md",
            summary="Database service",
            content_type="text/markdown",
        )
        # Related entity of different type
        config = Entity(
            title="service_config",
            entity_type="test",
            path_id="config/service",
            file_path="config/service.md",
            summary="Service configuration",
            content_type="text/markdown",
        )
        session.add_all([core, dbe, config])
        await session.flush()

        # Create relations in both directions
        relations = [
            # core -> db (depends_on)
            Relation(from_id=core.id, to_id=dbe.id, relation_type="depends_on"),
            # config -> core (configures)
            Relation(from_id=config.id, to_id=core.id, relation_type="configures"),
        ]
        session.add_all(relations)

    # Test 1: List without related entities
    services = await entity_repository.list_entities(entity_type="test", include_related=False)
    assert len(services) == 2
    service_names = {s.title for s in services}
    assert service_names == {"service_config", "db_service"}

    # Test 2: List services with related entities
    services_and_related = await entity_repository.list_entities(
        entity_type="test", include_related=True
    )
    assert len(services_and_related) == 3
    # Should include both services and the config
    entity_names = {e.title for e in services_and_related}
    assert entity_names == {"core_service", "db_service", "service_config"}

    # Test 3: Verify relations are loaded
    core_service = next(e for e in services_and_related if e.title == "core_service")
    assert len(core_service.outgoing_relations) > 0  # Has incoming relation from config
    assert len(core_service.incoming_relations) > 0  # Has outgoing relation to db
