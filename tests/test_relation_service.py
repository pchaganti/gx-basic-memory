"""Tests for RelationService."""
import pytest
import pytest_asyncio

from basic_memory.schemas import EntityRequest, RelationRequest

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def sample_entities(entity_service):
    """Create two sample entities for testing relations"""
    entity1_data = EntityRequest(
        name="test_entity_1",
        entity_type="test_type",
        observations=[],
        relations=[]
    )
    entity2_data = EntityRequest(
        name="test_entity_2",
        entity_type="test_type",
        observations=[],
        relations=[]
    )
    entity1 = await entity_service.create_entity(entity1_data)
    entity2 = await entity_service.create_entity(entity2_data)
    return entity1, entity2


def normalize_whitespace(s: str) -> str:
    """Normalize whitespace in a string for comparison."""
    return ' '.join(s.split())


async def test_create_relation(relation_service, sample_entities):
    """Test creating a basic relation between two entities"""
    entity1, entity2 = sample_entities
    
    relation_data = RelationRequest(
        from_id=entity1.id,
        to_id=entity2.id,
        relation_type="test_relation"
    )
    
    relation = await relation_service.create_relation(relation_data)
    
    # Check relation was created correctly
    assert relation.from_id == entity1.id
    assert relation.to_id == entity2.id
    assert relation.relation_type == "test_relation"

    # Verify database was updated with correct IDs
    db_relation = await relation_service.relation_repo.find_by_id(relation.id)
    assert db_relation is not None
    assert db_relation.from_id == entity1.id
    assert db_relation.to_id == entity2.id
    assert db_relation.relation_type == "test_relation"



async def test_create_relation_with_context(relation_service, sample_entities):
    """Test creating a relation with context information"""
    entity1, entity2 = sample_entities
    
    relation_data = RelationRequest(
        from_id=entity1.id,
        to_id=entity2.id,
        relation_type="test_relation",
        context="test context"
    )
    
    relation = await relation_service.create_relation(relation_data)
    
    assert relation.context == "test context"

    # Verify context in database
    db_relation = await relation_service.relation_repo.find_by_id(relation.id)
    assert db_relation.context == "test context"