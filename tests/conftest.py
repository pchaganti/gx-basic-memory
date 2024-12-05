"""Common test fixtures for basic-memory."""
import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from basic_memory.models import Base, Entity as DbEntity, Observation as DbObservation, Relation as DbRelation
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository
from basic_memory.services import EntityService, ObservationService, RelationService

@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create an async engine using in-memory SQLite database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
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
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@pytest_asyncio.fixture
async def entity_repo(session):
    """Create an EntityRepository instance."""
    return EntityRepository(session, DbEntity)

@pytest_asyncio.fixture
async def observation_repo(session):
    """Create an ObservationRepository instance."""
    return ObservationRepository(session, DbObservation)

@pytest_asyncio.fixture
async def relation_repo(session):
    """Create a RelationRepository instance."""
    return RelationRepository(session, DbRelation)

@pytest_asyncio.fixture
async def entity_service(session, entity_repo):
    """Fixture providing initialized EntityService with temp directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        
        service = EntityService(project_path, entity_repo)
        yield service

@pytest_asyncio.fixture
async def observation_service(session, observation_repo):
    """Fixture providing initialized ObservationService."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        
        service = ObservationService(project_path, observation_repo)
        yield service

@pytest_asyncio.fixture
async def relation_service(session, relation_repo):
    """Fixture providing initialized RelationService."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test-project"
        entities_path = project_path / "entities"
        entities_path.mkdir(parents=True)
        
        service = RelationService(project_path, relation_repo)
        yield service

@pytest_asyncio.fixture
async def test_entity(entity_service):
    """Create a test entity for reuse in tests."""
    return await entity_service.create_entity(
        name="Test Entity",
        entity_type="test",
    )