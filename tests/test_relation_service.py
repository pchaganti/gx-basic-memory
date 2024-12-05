import pytest
from datetime import datetime, UTC
from pathlib import Path

from basic_memory.models import Entity as DbEntity
from basic_memory.models import Relation as DbRelation
from basic_memory.schemas import Entity, Relation
from basic_memory.services import RelationService, EntityService
from basic_memory.repository import EntityRepository, RelationRepository


@pytest.fixture
async def entity_repo(db_session):
    return EntityRepository(db_session)


@pytest.fixture
async def relation_repo(db_session):
    return RelationRepository(db_session)


@pytest.fixture
async def entity_service(tmp_path, entity_repo):
    return EntityService(tmp_path, entity_repo)


@pytest.fixture
async def relation_service(tmp_path, relation_repo):
    return RelationService(tmp_path, relation_repo)


@pytest.fixture
async def sample_entities(entity_service):
    """Create two sample entities for testing relations"""
    entity1 = await entity_service.create_entity(
        name="test_entity_1",
        entity_type="test_type"
    )
    entity2 = await entity_service.create_entity(
        name="test_entity_2",
        entity_type="test_type"
    )
    return entity1, entity2


async def test_create_relation(relation_service, sample_entities):
    """Test creating a basic relation between two entities"""
    entity1, entity2 = sample_entities
    
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type="test_relation"
    )
    
    assert relation.from_id == entity1.id
    assert relation.to_id == entity2.id
    assert relation.relation_type == "test_relation"
    
    # Verify relation was added to source entity's relations
    assert hasattr(entity1, 'relations')
    assert len(entity1.relations) == 1
    assert entity1.relations[0].id == relation.id
    
    # Verify file was written with relation
    entity_file = relation_service.entities_path / f"{entity1.id}.md"
    assert entity_file.exists()
    content = entity_file.read_text()
    assert "## Relations" in content
    assert f"[{entity2.id}] test_relation" in content
    
    # Verify database was updated
    db_relation = await relation_service.relation_repo.find_by_id(relation.id)
    assert db_relation is not None
    assert db_relation.from_id == entity1.id
    assert db_relation.to_id == entity2.id
    assert db_relation.relation_type == "test_relation"


async def test_create_relation_with_context(relation_service, sample_entities):
    """Test creating a relation with context information"""
    entity1, entity2 = sample_entities
    
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type="test_relation",
        context="test context"
    )
    
    assert relation.context == "test context"
    
    # Verify context in file
    entity_file = relation_service.entities_path / f"{entity1.id}.md"
    content = entity_file.read_text()
    assert f"[{entity2.id}] test_relation | test context" in content
    
    # Verify context in database
    db_relation = await relation_service.relation_repo.find_by_id(relation.id)
    assert db_relation.context == "test context"


async def test_get_entity_relations(relation_service, sample_entities):
    """Test retrieving relations for an entity"""
    entity1, entity2 = sample_entities
    
    # Create test relation
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type="test_relation"
    )
    
    # Get relations from entity
    relations = await relation_service.get_entity_relations(entity1)
    
    assert len(relations) == 1
    assert relations[0].from_id == entity1.id
    assert relations[0].to_id == entity2.id
    assert relations[0].relation_type == "test_relation"


async def test_delete_relation(relation_service, sample_entities):
    """Test deleting a relation"""
    entity1, entity2 = sample_entities
    
    # Create then delete a relation
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type="test_relation"
    )
    
    success = await relation_service.delete_relation(entity1, relation.id)
    assert success is True
    
    # Verify removed from entity relations
    assert not entity1.relations or relation.id not in [r.id for r in entity1.relations]
    
    # Verify removed from file
    entity_file = relation_service.entities_path / f"{entity1.id}.md"
    content = entity_file.read_text()
    assert f"[{entity2.id}] test_relation" not in content
    
    # Verify removed from database
    db_relation = await relation_service.relation_repo.find_by_id(relation.id)
    assert db_relation is None


async def test_rebuild_relation_index(relation_service, sample_entities):
    """Test rebuilding the relation index from files"""
    entity1, entity2 = sample_entities
    
    # Create some test relations
    relation1 = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type="test_relation_1"
    )
    relation2 = await relation_service.create_relation(
        from_entity=entity2,
        to_entity=entity1,
        relation_type="test_relation_2"
    )
    
    # Clear the database relations
    await relation_service.relation_repo.execute_query(
        'DELETE FROM relation'
    )
    
    # Rebuild index
    await relation_service.rebuild_relation_index()
    
    # Verify relations were restored
    db_relations = await relation_service.relation_repo.execute_query(
        'SELECT * FROM relation'
    )
    relations = db_relations.scalars().all()
    
    assert len(relations) == 2
    relation_types = {r.relation_type for r in relations}
    assert relation_types == {"test_relation_1", "test_relation_2"}
