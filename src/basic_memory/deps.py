"""Dependency injection functions for basic-memory services."""

from pathlib import Path
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)

from basic_memory import db
from basic_memory.config import ProjectConfig, config
from basic_memory.db import DatabaseType
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.services import (
    EntityService,
    ObservationService,
    RelationService,
    DocumentService,
)


## project


def get_project_config() -> ProjectConfig:
    return config


ProjectConfigDep = Annotated[ProjectConfig, Depends(get_project_config)]


def get_project_path(project_config: ProjectConfigDep) -> Path:
    return Path(project_config.path)


ProjectPathDep = Annotated[Path, Depends(get_project_path)]

## sqlalchemy


async def get_engine_factory(
    project_path: ProjectPathDep, db_type=DatabaseType.FILESYSTEM
) -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    async with db.engine_session_factory(project_path=project_path, db_type=db_type) as (
        engine,
        session_maker,
    ):
        yield engine, session_maker


EngineFactoryDep = Annotated[
    tuple[AsyncEngine, async_sessionmaker[AsyncSession]], Depends(get_engine_factory)
]


async def get_session_maker(engine_factory: EngineFactoryDep) -> async_sessionmaker[AsyncSession]:
    """Get session maker for tests."""
    _, session_maker = engine_factory
    return session_maker


SessionMakerDep = Annotated[async_sessionmaker, Depends(get_session_maker)]

## repositories


async def get_entity_repository(
    session_maker: SessionMakerDep,
) -> EntityRepository:
    """Create an EntityRepository instance."""
    return EntityRepository(session_maker)


EntityRepositoryDep = Annotated[EntityRepository, Depends(get_entity_repository)]


async def get_observation_repository(
    session_maker: SessionMakerDep,
) -> ObservationRepository:
    """Create an ObservationRepository instance."""
    return ObservationRepository(session_maker)


ObservationRepositoryDep = Annotated[ObservationRepository, Depends(get_observation_repository)]


async def get_relation_repository(
    session_maker: SessionMakerDep,
) -> RelationRepository:
    """Create a RelationRepository instance."""
    return RelationRepository(session_maker)


RelationRepositoryDep = Annotated[RelationRepository, Depends(get_relation_repository)]


async def get_document_repository(
    session_maker: SessionMakerDep,
) -> DocumentRepository:
    """Create a DocumentRepository instance."""
    return DocumentRepository(session_maker)


DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]

## services


async def get_entity_service(entity_repository: EntityRepositoryDep) -> EntityService:
    """Create EntityService with repository."""
    return EntityService(entity_repository)


EntityServiceDep = Annotated[EntityService, Depends(get_entity_service)]


async def get_observation_service(
    observation_repository: ObservationRepositoryDep,
) -> ObservationService:
    """Create ObservationService with repository."""
    return ObservationService(observation_repository)


ObservationServiceDep = Annotated[ObservationService, Depends(get_observation_service)]


async def get_relation_service(relation_repository: RelationRepositoryDep) -> RelationService:
    """Create RelationService with repository."""
    return RelationService(relation_repository)


RelationServiceDep = Annotated[RelationService, Depends(get_relation_service)]


async def get_document_service(document_repository: DocumentRepositoryDep) -> DocumentService:
    """Create RelationService with repository."""
    return DocumentService(document_repository)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
