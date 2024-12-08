"""Service for managing observations in both filesystem and database."""
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import select, delete

from basic_memory.models import Observation as DbObservation
from basic_memory.repository import ObservationRepository
from basic_memory.schemas import Entity, Observation, ObservationIn
from basic_memory.models import Observation as ObservationModel
from . import ServiceError, DatabaseSyncError


class ObservationService:
    """
    Service for managing observations in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, observation_repo: ObservationRepository):
        self.project_path = project_path
        self.observation_repo = observation_repo
        
    async def add_observations(self, entity: Entity, observations: List[ObservationIn]) -> List[Observation]:
        """
        Add multiple observations to an entity.
        Returns the created observations with IDs set.
        """
        created_observations = []

        async def add_observation(observation: ObservationIn) -> Observation:
            try:
                db_observation = await self.observation_repo.create({
                    'entity_id': entity.id,
                    'content': observation.content,
                    'context': observation.context,
                    'created_at': datetime.now(UTC)
                })
                # Convert db model to schema
                return Observation(
                    id=db_observation.id,
                    content=db_observation.content,
                    context=db_observation.context
                )
            except Exception as e:
                raise DatabaseSyncError(f"Failed to add observation to database: {str(e)}") from e

        # Add each observation and collect the results
        created_observations = [await add_observation(obs) for obs in observations]

        # Update entity in memory with the created observations that have IDs
        entity.observations.extend(created_observations)
        return created_observations

    async def search_observations(self, query: str) -> List[ObservationModel]:
        """
        Search for observations across all entities.
        
        Args:
            query: Text to search for in observation content
            
        Returns:
            List of matching observations with their entity contexts
        """
        result = await self.observation_repo.execute_query(
            select(DbObservation).filter(
                DbObservation.content.contains(query)
            )
        )
        return [
            Observation(content=obs.content)
            for obs in result.scalars().all()
        ]
        
    async def get_observations_by_context(self, context: str) -> List[ObservationModel]:
        """Get all observations with a specific context."""
        db_observations = await self.observation_repo.find_by_context(context)
        return [
            Observation(content=obs.content) 
            for obs in db_observations
        ]

    async def rebuild_observation_index(self, entity: Entity) -> None:
        """
        Rebuild the observation database index for a specific entity.
        Used for recovery or ensuring sync.
        """
        # Clear existing observations for this entity
        await self.observation_repo.execute_query(
            delete(DbObservation).where(DbObservation.entity_id == entity.id)
        )
        
        # Rebuild from entity's observations
        for obs in entity.observations:
            await self.observation_repo.create({
                'entity_id': entity.id,
                'content': obs.content,
                'context': obs.context,
                'created_at': datetime.now(UTC)
            })