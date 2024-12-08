"""Service for managing observations in both filesystem and database."""
from datetime import datetime, UTC
from pathlib import Path
from typing import List
from sqlalchemy import select, delete

from basic_memory.models import Observation
from basic_memory.repository import ObservationRepository
from basic_memory.schemas import EntityIn, ObservationIn
from . import DatabaseSyncError


class ObservationService:
    """
    Service for managing observations in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, observation_repo: ObservationRepository):
        self.project_path = project_path
        self.observation_repo = observation_repo
        
    async def add_observations(self, entity: EntityIn, observations: List[ObservationIn]) -> List[Observation]:
        """
        Add multiple observations to an entity.
        Returns the created observations with IDs set.
        """
        print(f"\nObservationService.add_observations called for entity {entity.id}")
        print(f"Adding {len(observations)} observations")

        async def add_observation(observation: ObservationIn) -> Observation:
            try:
                return await self.observation_repo.create({
                    'entity_id': entity.id,
                    'content': observation.content,
                    'context': observation.context,
                    'created_at': datetime.now(UTC)
                })
            except Exception as e:
                raise DatabaseSyncError(f"Failed to add observation to database: {str(e)}") from e

        # Add each observation and collect the results
        created_observations = [await add_observation(obs) for obs in observations]
        print(f"Created {len(created_observations)} observations in DB")
        return created_observations

    async def search_observations(self, query: str) -> List[Observation]:
        """
        Search for observations across all entities.
        
        Args:
            query: Text to search for in observation content
            
        Returns:
            List of matching observations with their entity contexts
        """
        result = await self.observation_repo.execute_query(
            select(Observation).filter(
                Observation.content.contains(query)
            )
        )
        return [
            Observation(content=obs.content)
            for obs in result.scalars().all()
        ]
        
    async def get_observations_by_context(self, context: str) -> List[Observation]:
        """Get all observations with a specific context."""
        db_observations = await self.observation_repo.find_by_context(context)
        return [
            Observation(content=obs.content) 
            for obs in db_observations
        ]