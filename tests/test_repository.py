import pytest
import pytest_asyncio
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from basic_memory.models import Base, Entity, Observation, Relation
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create an async engine using in-memory SQLite database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",  # In-memory database
        echo=False  # Set to True for SQL logging
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Create an async session factory and yield a session"""
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def entity_repository(session: AsyncSession):
    """Create an EntityRepository instance"""
    yield EntityRepository(session, Entity)


@pytest_asyncio.fixture(scope="function")
async def observation_repository(session: AsyncSession):
    """Create an ObservationRepository instance"""
    return ObservationRepository(session, Observation)


@pytest_asyncio.fixture(scope="function")
async def relation_repository(session: AsyncSession):
    """Create a RelationRepository instance"""
    return RelationRepository(session, Relation)


@pytest_asyncio.fixture(scope="function")
async def sample_entity(entity_repository: EntityRepository):
    """Create a sample entity for testing"""
    entity_data = {
        'id': '20240102-test-entity',
        'name': 'Test Entity',
        'entity_type': 'test',
        'description': 'A test entity',
        'references': 'Test references'
    }
    return await entity_repository.create(entity_data)


class TestEntityRepository:
    async def test_create_entity(self, entity_repository: EntityRepository):
        """Test creating a new entity"""
        entity_data = {
            'id': '20240102-test',
            'name': 'Test',
            'entity_type': 'test',
            'description': 'Test description',
            'references': 'Test references'
        }
        entity = await entity_repository.create(entity_data)
        
        assert entity.id == '20240102-test'
        assert entity.name == 'Test'
        assert entity.description == 'Test description'
        assert isinstance(entity.created_at, datetime)
        assert entity.created_at.tzinfo == UTC

    async def test_find_by_id(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test finding an entity by ID"""
        found = await entity_repository.find_by_id(sample_entity.id)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.name == sample_entity.name

    async def test_find_by_name(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test finding an entity by name"""
        found = await entity_repository.find_by_name(sample_entity.name)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.name == sample_entity.name

    async def test_update_entity(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test updating an entity"""
        updated = await entity_repository.update(
            sample_entity.id,
            {'description': 'Updated description'}
        )
        assert updated is not None
        assert updated.description == 'Updated description'
        assert updated.name == sample_entity.name  # Other fields unchanged

    async def test_delete_entity(self, entity_repository: EntityRepository, sample_entity: Entity):
        """Test deleting an entity"""
        success = await entity_repository.delete(sample_entity.id)
        assert success is True
        
        # Verify it's gone
        found = await entity_repository.find_by_id(sample_entity.id)
        assert found is None


class TestObservationRepository:
    @pytest_asyncio.fixture(scope="function")
    async def sample_observation(self, observation_repository: ObservationRepository, sample_entity: Entity):
        """Create a sample observation for testing"""
        observation_data = {
            'entity_id': sample_entity.id,
            'content': 'Test observation',
            'context': 'test-context'
        }
        return await observation_repository.create(observation_data)

    async def test_create_observation(
        self,
        observation_repository: ObservationRepository,
        sample_entity: Entity
    ):
        """Test creating a new observation"""
        observation_data = {
            'entity_id': sample_entity.id,
            'content': 'Test content',
            'context': 'test-context'
        }
        observation = await observation_repository.create(observation_data)
        
        assert observation.entity_id == sample_entity.id
        assert observation.content == 'Test content'
        assert observation.id is not None  # Should be auto-generated

    async def test_find_by_entity(
        self,
        observation_repository: ObservationRepository,
        sample_observation: Observation,
        sample_entity: Entity
    ):
        """Test finding observations by entity"""
        observations = await observation_repository.find_by_entity(sample_entity.id)
        assert len(observations) == 1
        assert observations[0].id == sample_observation.id
        assert observations[0].content == sample_observation.content

    async def test_find_by_context(
        self,
        observation_repository: ObservationRepository,
        sample_observation: Observation
    ):
        """Test finding observations by context"""
        observations = await observation_repository.find_by_context('test-context')
        assert len(observations) == 1
        assert observations[0].id == sample_observation.id


class TestRelationRepository:
    @pytest_asyncio.fixture(scope="function")
    async def related_entity(self, entity_repository: EntityRepository):
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