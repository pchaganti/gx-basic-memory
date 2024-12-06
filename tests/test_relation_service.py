"""Tests for RelationService."""
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from basic_memory.models import Relation as DbRelation
from basic_memory.repository import EntityRepository, RelationRepository
from basic_memory.services import (
    EntityService, RelationService,
    ServiceError, DatabaseSyncError, RelationError
)
from basic_memory.schemas import Entity, Relation
from basic_memory.fileio import read_entity_file, FileOperationError, write_entity_file

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


def normalize_whitespace(s: str) -> str:
    """Normalize whitespace in a string for comparison."""
    return ' '.join(s.split())


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


async def test_file_operation_error(relation_service, sample_entities, mocker):
    """Test handling of file operation errors."""
    entity1, entity2 = sample_entities
    
    # Add debug to see if mock is being called
    async def mock_write(*args, **kwargs):
        print("Mock write called with:", args, kwargs)
        raise FileOperationError("Mock file error")
    
    # Patch where the function is used, not where it's imported from
    mocker.patch('basic_memory.services.relation_service.write_entity_file', mock_write)
    
    with pytest.raises(FileOperationError):
        await relation_service.create_relation(
            from_entity=entity1,
            to_entity=entity2,
            relation_type="test_relation"
        )


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