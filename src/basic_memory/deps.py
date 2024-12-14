"""Dependency injection functions for basic-memory services."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Annotated

from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from basic_memory.config import ProjectConfig, config
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.services import EntityService, ObservationService, RelationService, MemoryService
from basic_memory import db

def get_project_config() -> ProjectConfig:
    return config
ProjectConfigDep = Annotated[ProjectConfig, Depends(get_project_config)]

def get_project_path(project_config: ProjectConfigDep) -> Path:
    return Path(project_config.path)
ProjectPathDep = Annotated[Path, Depends(get_project_path)]


async def get_engine(project_path: ProjectPathDep, db_type=db.DatabaseType.FILESYSTEM) -> AsyncGenerator[AsyncEngine, None]:
    async with db.engine(project_path, db_type) as engine:
        yield engine

EngineDep = Annotated[AsyncEngine, Depends(get_engine)]

async def get_session(engine: EngineDep) -> AsyncGenerator[AsyncSession, None]:
    async with db.session(engine) as session:
        yield session

AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_entity_repo(session: AsyncSessionDep) -> EntityRepository:
    """Get an EntityRepository instance."""
    return EntityRepository(session)  # Entity type is handled in EntityRepository.__init__

EntityRepositoryDep = Annotated[EntityRepository, Depends(get_entity_repo)]

async def get_observation_repo(session: AsyncSessionDep) -> ObservationRepository:
    """Get an ObservationRepository instance."""
    return ObservationRepository(session)

ObservationRepositoryDep = Annotated[ObservationRepository, Depends(get_observation_repo)]

async def get_relation_repo(session: AsyncSessionDep) -> RelationRepository:
    """Get a RelationRepository instance."""
    return RelationRepository(session)

RelationRepositoryDep = Annotated[RelationRepository, Depends(get_relation_repo)]

async def get_entity_service(
    project_path: ProjectPathDep,
    entity_repo: EntityRepositoryDep
) -> EntityService:
    """Get an EntityService instance."""
    return EntityService(project_path, entity_repo)

EntityServiceDep = Annotated[EntityService, Depends(get_entity_service)]

async def get_observation_service(
    project_path: ProjectPathDep,
    observation_repo: ObservationRepositoryDep
) -> ObservationService:
    """Get an ObservationService instance."""
    return ObservationService(project_path, observation_repo)

ObservationServiceDep = Annotated[ObservationService, Depends(get_observation_service)]

async def get_relation_service(
    project_path: ProjectPathDep,
    relation_repo: RelationRepositoryDep
) -> RelationService:
    """Get a RelationService instance."""
    return RelationService(project_path, relation_repo)

RelationServiceDep = Annotated[RelationService, Depends(get_relation_service)]

@asynccontextmanager
async def memory_service(
    project_path: ProjectPathDep,
    entity_service: EntityServiceDep,
    relation_service: RelationServiceDep,
    observation_service: ObservationServiceDep
) -> AsyncGenerator[MemoryService, None]:
    """Get a fully configured MemoryService instance."""
    yield MemoryService(
        project_path=project_path,
        entity_service=entity_service,
        relation_service=relation_service,
        observation_service=observation_service
    )

async def get_memory_service(
        project_path: ProjectPathDep,
        entity_service: EntityServiceDep,
        relation_service: RelationServiceDep,
        observation_service: ObservationServiceDep
) -> AsyncGenerator[MemoryService, None]:
    async with memory_service(project_path, entity_service, relation_service, observation_service) as service:
        yield service

MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]





