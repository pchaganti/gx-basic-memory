"""Tests for RelationRepository."""
import pytest
import pytest_asyncio
from basic_memory.models import Entity, Relation
from basic_memory.repository.relation_repository import RelationRepository

pytestmark = pytest.mark.asyncio


class TestRelationRepository:
    @pytest_asyncio.fixture(scope="function")
    async def related_entity(self, entity_repository):
        """Create a second entity for testing relations"""
        entity_data = {
            'id': '20240102-related',
            'name': 'Related Entity',
            'entity_type': 'test',
            'description': 'A related test entity',
            'references': ''
        }
        return await entity_repository.create(entity_data)

    @pytest_asyncio.fixture(scope="function")
    async def sample_relation(
        self,
        relation_repository: RelationRepository,
        sample_entity: Entity,
        related_entity: Entity
    ):
        """Create a sample relation for testing"""
        relation_data = {
            'from_id': sample_entity.id,
            'to_id': related_entity.id,
            'relation_type': 'test_relation',
            'context': 'test-context'
        }
        return await relation_repository.create(relation_data)

    async def test_create_relation(
        self,
        relation_repository: RelationRepository,
        sample_entity: Entity,
        related_entity: Entity
    ):
        """Test creating a new relation"""
        relation_data = {
            'from_id': sample_entity.id,
            'to_id': related_entity.id,
            'relation_type': 'test_relation',
            'context': 'test-context'
        }
        relation = await relation_repository.create(relation_data)
        
        assert relation.from_id == sample_entity.id
        assert relation.to_id == related_entity.id
        assert relation.relation_type == 'test_relation'
        assert relation.id is not None  # Should be auto-generated

    async def test_find_by_entities(
        self,
        relation_repository: RelationRepository,
        sample_relation: Relation,
        sample_entity: Entity,
        related_entity: Entity
    ):
        """Test finding relations between specific entities"""
        relations = await relation_repository.find_by_entities(
            sample_entity.id,
            related_entity.id
        )
        assert len(relations) == 1
        assert relations[0].id == sample_relation.id
        assert relations[0].relation_type == sample_relation.relation_type

    async def test_find_by_type(
        self,
        relation_repository: RelationRepository,
        sample_relation: Relation
    ):
        """Test finding relations by type"""
        relations = await relation_repository.find_by_type('test_relation')
        assert len(relations) == 1
        assert relations[0].id == sample_relation.id