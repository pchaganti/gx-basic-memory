import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from basic_memory.models import Relation as DbRelation
from basic_memory.schemas import Relation
from basic_memory.services import FileOperationError, DatabaseSyncError
from basic_memory.fileio import read_entity_file

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
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


# Helper function for comparing strings with variable whitespace
def normalize_whitespace(s: str) -> str:
    """Normalize whitespace in a string for comparison."""
    return ' '.join(s.split())


# Happy Path Tests

async def test_create_relation(relation_service, sample_entities):
    """Test creating a basic relation between two entities"""
    entity1, entity2 = sample_entities
    
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type="test_relation"
    )
    
    # Check Entity objects in relation
    assert relation.from_entity.id == entity1.id
    assert relation.to_entity.id == entity2.id
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
    
    # Verify database was updated with correct IDs
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
    assert relations[0].from_entity.id == entity1.id
    assert relations[0].to_entity.id == entity2.id
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
    await relation_service.relation_repo.execute_query(delete(DbRelation))
    
    # Rebuild index
    await relation_service.rebuild_relation_index()
    
    # Verify relations were restored using SQLAlchemy select
    query = select(DbRelation)
    result = await relation_service.relation_repo.execute_query(query)
    relations = result.scalars().all()
    
    assert len(relations) == 2
    relation_types = {r.relation_type for r in relations}
    assert relation_types == {"test_relation_1", "test_relation_2"}


# Error Path Tests

async def test_file_operation_error(relation_service, sample_entities, monkeypatch):
    """Test handling of file operation errors."""
    entity1, entity2 = sample_entities
    
    async def mock_write(*args, **kwargs):
        raise FileOperationError("Mock file error")
    
    monkeypatch.setattr('basic_memory.services.write_entity_file', mock_write)
    
    with pytest.raises(FileOperationError):
        await relation_service.create_relation(
            from_entity=entity1,
            to_entity=entity2,
            relation_type="test_relation"
        )


async def test_database_sync_error(relation_service, sample_entities, monkeypatch):
    """Test handling of database sync errors."""
    entity1, entity2 = sample_entities
    
    async def mock_create(*args, **kwargs):
        raise Exception("Mock DB error")
    
    monkeypatch.setattr(relation_service.relation_repo, "create", mock_create)
    
    with pytest.raises(DatabaseSyncError):
        await relation_service.create_relation(
            from_entity=entity1,
            to_entity=entity2,
            relation_type="test_relation"
        )


# Edge Cases

async def test_relation_with_special_characters(relation_service, sample_entities):
    """Test handling relations with special characters."""
    entity1, entity2 = sample_entities
    
    relation_type = "test & relation with @#$% special chars!"
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type=relation_type
    )
    
    assert relation.relation_type == relation_type
    
    # Verify file content
    entity = await read_entity_file(relation_service.entities_path, entity1.id)
    assert any(r.relation_type == relation_type for r in getattr(entity, 'relations', []))


async def test_very_long_relation_type(relation_service, sample_entities):
    """Test handling very long relation type."""
    entity1, entity2 = sample_entities
    
    long_type = "Very long relation type " * 20  # ~400 characters
    relation = await relation_service.create_relation(
        from_entity=entity1,
        to_entity=entity2,
        relation_type=long_type
    )
    
    assert relation.relation_type == long_type
    
    # Verify file content
    entity = await read_entity_file(relation_service.entities_path, entity1.id)
    # Compare with normalized whitespace
    stored_types = {normalize_whitespace(r.relation_type) for r in getattr(entity, 'relations', [])}
    assert normalize_whitespace(long_type) in stored_types