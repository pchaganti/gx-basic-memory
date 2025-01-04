"""Dependency injection functions for basic-memory services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)

from basic_memory import db
from basic_memory.config import ProjectConfig, config
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
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
from basic_memory.services.activity_service import ActivityService
from basic_memory.services.file_service import FileService
from basic_memory.services.knowledge import KnowledgeService


## project


def get_project_config() -> ProjectConfig:
    return config


ProjectConfigDep = Annotated[ProjectConfig, Depends(get_project_config)]


## sqlalchemy


async def get_engine_factory(
    project_config: ProjectConfigDep,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Get engine and session maker."""
    return await db.get_or_create_db(project_config.database_path)


EngineFactoryDep = Annotated[
    tuple[AsyncEngine, async_sessionmaker[AsyncSession]], Depends(get_engine_factory)
]


async def get_session_maker(engine_factory: EngineFactoryDep) -> async_sessionmaker[AsyncSession]:
    """Get session maker."""
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

async def get_file_service() -> FileService:
    return FileService()


FileServiceDep = Annotated[FileService, Depends(get_file_service)]


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


async def get_document_service(
    document_repository: DocumentRepositoryDep, project_config: ProjectConfigDep, file_service: FileServiceDep,
) -> DocumentService:
    """Create RelationService with repository."""
    return DocumentService(document_repository, project_config.documents_dir, file_service)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


async def get_activity_service(
    entity_service: EntityServiceDep,
    document_service: DocumentServiceDep,
    relation_service: RelationServiceDep,
) -> ActivityService:
    """Create ActivityService with dependencies."""
    return ActivityService(
        entity_service=entity_service,
        document_service=document_service,
        relation_service=relation_service,
    )


ActivityServiceDep = Annotated[ActivityService, Depends(get_activity_service)]




async def get_knowledge_writer() -> KnowledgeWriter:
    return KnowledgeWriter()


KnowledgeWriterDep = Annotated[KnowledgeWriter, Depends(get_knowledge_writer)]


async def get_knowledge_service(
    entity_service: EntityServiceDep,
    observation_service: ObservationServiceDep,
    relation_service: RelationServiceDep,
    file_service: FileServiceDep,
    knowledge_writer: KnowledgeWriterDep,
    project_config: ProjectConfigDep,
) -> KnowledgeService:
    """Create KnowledgeService with dependencies."""
    return KnowledgeService(
        entity_service=entity_service,
        observation_service=observation_service,
        relation_service=relation_service,
        file_service=file_service,
        knowledge_writer=knowledge_writer,
        base_path=project_config.knowledge_dir,
    )


KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
