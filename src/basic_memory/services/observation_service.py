"""Service for managing observations in both filesystem and database."""
from pathlib import Path
from typing import List, Sequence, Dict, Any
from sqlalchemy import select

from basic_memory.models import Observation as ObservationModel
from basic_memory.repository.observation_repository import ObservationRepository
from . import DatabaseSyncError
from basic_memory.schemas import Observation


class ObservationService:
    """
    Service for managing observations in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, observation_repo: ObservationRepository):
        self.project_path = project_path
        self.observation_repo = observation_repo
        
    async def add_observations(self, entity_id: str, observations: List[Observation]) -> List[ObservationModel]:
        """
        Add multiple observations to an entity.
        Returns the created observations with IDs set.
        """
        try:
            return await self.observation_repo.bulk_create([
                ObservationModel(
                    entity_id=entity_id,
                    content=observation,
                )
                for observation in observations
            ])
        except Exception as e:
            raise DatabaseSyncError(f"Failed to add observations to database: {str(e)}") from e

    async def delete_observations(self, entity_id: str, contents: List[str]) -> int:
        """
        Delete specific observations from an entity.
        
        Args:
            entity_id: ID of the entity
            contents: List of observation contents to delete
            
        Returns:
            Number of observations deleted
        """
        try:
            deleted = False
            for content in contents:
                result = await self.observation_repo.delete_by_fields(
                    entity_id=entity_id,
                    content=content
                )
                if result:
                    deleted = True
            return deleted
        except Exception as e:
            raise DatabaseSyncError(f"Failed to delete observations from database: {str(e)}") from e

    async def delete_by_entity(self, entity_id: str) -> bool:
        """
        Delete all observations for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            True if any observations were deleted
        """
        try:
            return await self.observation_repo.delete_by_fields(entity_id=entity_id)
        except Exception as e:
            raise DatabaseSyncError(f"Failed to delete observations from database: {str(e)}") from e

    async def search_observations(self, query: str) -> List[ObservationModel]:
        """
        Search for observations across all entities.
        
        Args:
            query: Text to search for in observation content
            
        Returns:
            List of matching observations with their entity contexts
        """
        result = await self.observation_repo.execute_query(
            select(ObservationModel).filter(
                ObservationModel.content.contains(query)
            )
        )
        return [
            ObservationModel(content=obs.content)
            for obs in result.scalars().all()
        ]
        
    async def get_observations_by_context(self, context: str) -> Sequence[ObservationModel]:
        """Get all observations with a specific context."""
        return await self.observation_repo.find_by_context(context)
