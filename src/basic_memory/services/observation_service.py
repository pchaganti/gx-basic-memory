"""Service for managing observations in both filesystem and database."""
from pathlib import Path
from typing import List, Sequence
from sqlalchemy import select

from basic_memory.models import Observation
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.schemas import ObservationIn
from . import DatabaseSyncError


class ObservationService:
    """
    Service for managing observations in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, observation_repo: ObservationRepository):
        self.project_path = project_path
        self.observation_repo = observation_repo
        
    async def add_observations(self, entity_id: str, observations: List[ObservationIn]) -> List[Observation]:
        """
        Add multiple observations to an entity.
        Returns the created observations with IDs set.
        """
        try:
            return await self.observation_repo.bulk_create([
                Observation(
                    entity_id=entity_id,
                    content=observation,
                )
                for observation in observations
            ])
        except Exception as e:
            raise DatabaseSyncError(f"Failed to add observations to database: {str(e)}") from e

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
        
    async def get_observations_by_context(self, context: str) -> Sequence[Observation]:
        """Get all observations with a specific context."""
        return await self.observation_repo.find_by_context(context)
