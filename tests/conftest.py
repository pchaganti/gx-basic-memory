"""Common test fixtures."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.db import DatabaseType
from basic_memory.markdown import EntityParser
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models import Base
from basic_memory.models.knowledge import Entity, Observation, ObservationCategory, Relation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.services import (
    EntityService,
    ObservationService,
    RelationService,
)
from basic_memory.services.activity_service import ActivityService
from basic_memory.services.file_service import FileService
from basic_memory.services.link_resolver import LinkResolver
from basic_memory.services.search_service import SearchService
from basic_memory.sync import FileChangeScanner
from basic_memory.sync.entity_sync_service import EntitySyncService
from basic_memory.sync.sync_service import SyncService


@pytest_asyncio.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
def test_config(tmp_path) -> ProjectConfig:
    """Test configuration using in-memory DB."""
    config = ProjectConfig(
        name="test",
    )
    config.home = tmp_path

    (tmp_path / config.home.name).mkdir(parents=True, exist_ok=True)
    return config


@pytest_asyncio.fixture(scope="function")
async def engine_factory(
    test_config,
) -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    """Create engine and session factory using in-memory SQLite database."""
    async with db.engine_session_factory(
        db_path=test_config.database_path, db_type=DatabaseType.MEMORY
    ) as (engine, session_maker):
        # Initialize database
        async with db.scoped_session(session_maker) as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))
            conn = await session.connection()
            await conn.run_sync(Base.metadata.create_all)

        yield engine, session_maker


@pytest_asyncio.fixture
async def session_maker(engine_factory) -> async_sessionmaker[AsyncSession]:
    """Get session maker for tests."""
    _, session_maker = engine_factory
    return session_maker


@pytest_asyncio.fixture(scope="function")
async def entity_repository(session_maker: async_sessionmaker[AsyncSession]) -> EntityRepository:
    """Create an EntityRepository instance."""
    return EntityRepository(session_maker)


@pytest_asyncio.fixture(scope="function")
async def observation_repository(
    session_maker: async_sessionmaker[AsyncSession],
) -> ObservationRepository:
    """Create an ObservationRepository instance."""
    return ObservationRepository(session_maker)


@pytest_asyncio.fixture(scope="function")
async def relation_repository(
    session_maker: async_sessionmaker[AsyncSession],
) -> RelationRepository:
    """Create a RelationRepository instance."""
    return RelationRepository(session_maker)


@pytest_asyncio.fixture
async def entity_service(
    entity_repository: EntityRepository, file_service: FileService
) -> EntityService:
    """Create EntityService with repository."""
    return EntityService(entity_repository=entity_repository, file_service=file_service)


@pytest_asyncio.fixture
async def relation_service(
    relation_repository: RelationRepository,
    entity_repository: EntityRepository,
    file_service: FileService,
) -> RelationService:
    """Create RelationService with repository."""
    return RelationService(
        relation_repository=relation_repository,
        entity_repository=entity_repository,
        file_service=file_service,
    )


@pytest_asyncio.fixture
async def observation_service(
    observation_repository: ObservationRepository,
    entity_repository: EntityRepository,
    file_service: FileService,
) -> ObservationService:
    """Create ObservationService with repository."""
    return ObservationService(observation_repository, entity_repository, file_service)


@pytest.fixture
def file_service(test_config: ProjectConfig, knowledge_writer: KnowledgeWriter) -> FileService:
    """Create FileService instance."""
    return FileService(test_config.home, knowledge_writer)


@pytest.fixture
def knowledge_writer():
    """Create writer instance."""
    return KnowledgeWriter()


@pytest.fixture
def link_resolver(entity_repository: EntityRepository, search_service: SearchService):
    """Create parser instance."""
    return LinkResolver(entity_repository, search_service)


@pytest.fixture
def entity_parser(test_config):
    """Create parser instance."""
    return EntityParser(test_config.home)


@pytest_asyncio.fixture
def file_change_scanner(entity_repository) -> FileChangeScanner:
    """Create FileChangeScanner instance."""
    return FileChangeScanner(entity_repository)


@pytest_asyncio.fixture
async def activity_service(entity_service, relation_service):
    """Create activity service with real dependencies."""
    return ActivityService(entity_service, relation_service)


@pytest_asyncio.fixture
async def entity_sync_service(
    entity_repository: EntityRepository,
    observation_repository: ObservationRepository,
    relation_repository: RelationRepository,
    link_resolver: LinkResolver,
) -> EntitySyncService:
    """Create EntitySyncService with repository."""
    return EntitySyncService(entity_repository, observation_repository, relation_repository, link_resolver)


@pytest_asyncio.fixture
async def sync_service(
    entity_sync_service: EntitySyncService,
    file_change_scanner: FileChangeScanner,
    entity_parser: EntityParser,
    entity_repository: EntityRepository,
    search_service: SearchService,
) -> SyncService:
    """Create sync service for testing."""
    return SyncService(
        scanner=file_change_scanner,
        entity_sync_service=entity_sync_service,
        entity_repository=entity_repository,
        entity_parser=entity_parser,
        search_service=search_service,
    )


@pytest_asyncio.fixture
async def search_repository(session_maker):
    """Create SearchRepository instance"""
    return SearchRepository(session_maker)


@pytest_asyncio.fixture(autouse=True)
async def init_search_index(search_service):
    await search_service.init_search_index()


@pytest_asyncio.fixture
async def search_service(
    search_repository: SearchRepository,
    entity_repository: EntityRepository,
) -> SearchService:
    """Create and initialize search service"""
    service = SearchService(search_repository, entity_repository)
    await service.init_search_index()
    return service


@pytest_asyncio.fixture(scope="function")
async def sample_entity(entity_repository: EntityRepository) -> Entity:
    """Create a sample entity for testing."""
    entity_data = {
        "title": "Test Entity",
        "entity_type": "test",
        "summary": "A test entity",
        "permalink": "test/test_entity",
        "file_path": "test/test_entity.md",
        "content_type": "text/markdown",
    }
    return await entity_repository.create(entity_data)


@pytest_asyncio.fixture
async def full_entity(sample_entity, entity_repository):
    """Create a search test entity."""

    search_entity = await entity_repository.create({
        "title": "Search Entity",
        "entity_type": "test",
        "summary": "A searchable entity",
        "permalink": "test/search_entity",
        "file_path": "test/search_entity.md",
        "content_type": "text/markdown",
    })

    observations = [
        Observation(content="Tech note", category=ObservationCategory.TECH),
        Observation(content="Design note", category=ObservationCategory.DESIGN),
    ]
    relations = [
        Relation(from_id=search_entity.id, to_id=sample_entity.id, relation_type="out1"),
        Relation(from_id=search_entity.id, to_id=sample_entity.id, relation_type="out2"),
    ]
    search_entity.observations = observations
    search_entity.outgoing_relations = relations
    return await entity_repository.add(search_entity)

@pytest_asyncio.fixture
async def test_graph(entity_repository, search_service):
    """Create a test knowledge graph with entities, relations and observations."""
    # Create some test entities
    entities = [
        Entity(
            title="Root Entity",
            entity_type="test",
            permalink="test/root",
            file_path="test/root.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Connected Entity 1",
            entity_type="test",
            permalink="test/connected1",
            file_path="test/connected1.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Connected Entity 2",
            entity_type="test",
            permalink="test/connected2",
            file_path="test/connected2.md",
            content_type="text/markdown",
        ),
        Entity(
            title="Deep Entity",
            entity_type="deep",
            permalink="test/deep",
            file_path="test/deep.md",
            content_type="text/markdown",
        ),
    ]
    entities = await entity_repository.add_all(entities)
    root, conn1, conn2, deep = entities

    # Add some observations
    root.observations = [
        Observation(content="Root note 1", category=ObservationCategory.NOTE),
        Observation(content="Root tech note", category=ObservationCategory.TECH),
    ]

    conn1.observations = [
        Observation(content="Connected 1 note", category=ObservationCategory.NOTE)
    ]

    # Add relations
    relations = [
        # Direct connections to root
        Relation(from_id=root.id, to_id=conn1.id, relation_type="connects_to"),
        Relation(from_id=conn2.id, to_id=root.id, relation_type="connected_from"),
        # Deep connection
        Relation(from_id=conn1.id, to_id=deep.id, relation_type="deep_connection"),
    ]

    root.outgoing_relations = [relations[0]]
    conn1.outgoing_relations = [relations[2]]
    conn2.outgoing_relations = [relations[1]]

    # Save relations
    root = await entity_repository.add(root)
    conn1 = await entity_repository.add(conn1)
    conn2 = await entity_repository.add(conn2)

    # Index everything for search
    for entity in entities:
        await search_service.index_entity(entity)

    return {
        "root": root,
        "connected1": conn1,
        "connected2": conn2,
        "deep": deep,
        "observations": root.observations + conn1.observations,
        "relations": relations,
    }
