"""Dependency injection functions for basic-memory services."""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory.models import Entity as DbEntity, Observation as DbObservation, Relation as DbRelation
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository
from basic_memory.services import EntityService, ObservationService, RelationService, MemoryService

async def get_entity_repo(session: AsyncSession) -> EntityRepository:
    """Get an EntityRepository instance."""
    return EntityRepository(session, DbEntity)

async def get_observation_repo(session: AsyncSession) -> ObservationRepository:
    """Get an ObservationRepository instance."""
    return ObservationRepository(session, DbObservation)

async def get_relation_repo(session: AsyncSession) -> RelationRepository:
    """Get a RelationRepository instance."""
    return RelationRepository(session, DbRelation)

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