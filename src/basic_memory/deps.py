"""Dependency injection functions for basic-memory services."""
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from basic_memory.models import Entity as DbEntity, Observation as DbObservation, Relation as DbRelation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.services import EntityService, ObservationService, RelationService, MemoryService
from basic_memory.db import DatabaseType, get_database_url, init_database, get_session

async def get_entity_repo(session: AsyncSession) -> EntityRepository:
    """Get an EntityRepository instance."""
    return EntityRepository(session)  # Entity type is handled in EntityRepository.__init__

async def get_observation_repo(session: AsyncSession) -> ObservationRepository:
    """Get an ObservationRepository instance."""
    return ObservationRepository(session)

async def get_relation_repo(session: AsyncSession) -> RelationRepository:
    """Get a RelationRepository instance."""
    return RelationRepository(session)

async def get_entity_service(
    project_path: Path,
    entity_repo: EntityRepository
) -> EntityService:
    """Get an EntityService instance."""
    return EntityService(project_path, entity_repo)

async def get_observation_service(
    project_path: Path,
    observation_repo: ObservationRepository
) -> ObservationService:
    """Get an ObservationService instance."""
    return ObservationService(project_path, observation_repo)

async def get_relation_service(
    project_path: Path,
    relation_repo: RelationRepository
) -> RelationService:
    """Get a RelationService instance."""
    return RelationService(project_path, relation_repo)

async def get_memory_service(
    project_path: Path,
    entity_service: EntityService,
    relation_service: RelationService,
    observation_service: ObservationService
) -> MemoryService:
    """Get a fully configured MemoryService instance."""
    return MemoryService(
        project_path=project_path,
        entity_service=entity_service,
        relation_service=relation_service,
        observation_service=observation_service
    )

@asynccontextmanager
async def get_engine(project_path: Path):
    """Get database engine for project with proper lifecycle management."""
    url = get_database_url(DatabaseType.FILESYSTEM, project_path)
    engine = await init_database(url)
    try:
        yield engine
    finally:
        await engine.dispose()

@asynccontextmanager
async def get_services(engine: AsyncEngine, project_path: Path):
    """Get all services with proper session and lifecycle management."""
    async with get_session(engine) as session:
        # Create repos
        entity_repo = await get_entity_repo(session)
        observation_repo = await get_observation_repo(session)
        relation_repo = await get_relation_repo(session)

        # Create services
        entity_service = await get_entity_service(project_path, entity_repo)
        observation_service = await get_observation_service(project_path, observation_repo)
        relation_service = await get_relation_service(project_path, relation_repo)

        # Create memory service
        memory_service = await get_memory_service(
            project_path=project_path,
            entity_service=entity_service,
            relation_service=relation_service,
            observation_service=observation_service
        )

        yield memory_service

@asynccontextmanager
async def get_project_services(project_path: Path):
    """Get all services for a project with full lifecycle management."""
    async with get_engine(project_path) as engine:
        async with get_services(engine, project_path) as services:
            yield services