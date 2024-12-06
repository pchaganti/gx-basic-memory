"""Service for managing observations in both filesystem and database."""
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import select, delete

from basic_memory.models import Observation as DbObservation
from basic_memory.repository import ObservationRepository
from basic_memory.schemas import Entity, Observation
from basic_memory.fileio import (
    write_entity_file, read_entity_file,
    FileOperationError
)
from . import ServiceError, DatabaseSyncError


class ObservationService:
    """
    Service for managing observations in the filesystem and database.
    Follows the "filesystem is source of truth" principle.
    
    Observations are stored in entity markdown files and indexed in the database
    for efficient querying.
    """
    
    def __init__(self, project_path: Path, observation_repo: ObservationRepository):
        self.project_path = project_path
        self.entities_path = project_path / "entities"
        self.observation_repo = observation_repo
        
    async def add_observation(self, entity: Entity, content: str, 
                          context: Optional[str] = None) -> Observation:
        """
        Add a new observation to an entity.
        
        Args:
            entity: Entity to add observation to
            content: Content of the observation
            context: Optional context for the observation
            
        Returns:
            The created Observation
            
        Raises:
            FileOperationError: If file operations fail
            DatabaseSyncError: If database sync fails
        """
        # Create new observation
        observation = Observation(content=content)
        entity.observations.append(observation)
        
        # Update filesystem first (source of truth)
        await write_entity_file(self.entities_path, entity)
        
        # Update database index
        try:
            db_observation = await self.observation_repo.create({
                'id': f"{entity.id}-obs-{uuid4().hex[:8]}",
                'entity_id': entity.id,
                'content': content,
                'context': context,
                'created_at': datetime.now(UTC)
            })
            return observation
        except Exception as e:
            raise DatabaseSyncError(f"Failed to sync observation to database: {str(e)}") from e
            
    async def search_observations(self, query: str) -> List[Observation]:
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
        
    async def get_observations_by_context(self, context: str) -> List[Observation]:
        """Get all observations with a specific context."""
        db_observations = await self.observation_repo.find_by_context(context)
        return [
            Observation(content=obs.content) 
            for obs in db_observations
        ]

    async def rebuild_observation_index(self) -> None:
        """
        Rebuild the observation database index from filesystem contents.
        Used for recovery or ensuring sync.
        """
        # List all entity files
        if not self.entities_path.exists():
            return
            
        try:
            entity_files = list(self.entities_path.glob("*.md"))
        except Exception as e:
            raise FileOperationError(f"Failed to read entities directory: {str(e)}") from e
                
        # Clear existing observation index
        await self.observation_repo.execute_query(delete(DbObservation))
        
        # Rebuild from each entity file
        for entity_file in entity_files:
            try:
                entity = await read_entity_file(self.entities_path, entity_file.stem)
                for obs in entity.observations:
                    await self.observation_repo.create({
                        'id': f"{entity.id}-obs-{uuid4().hex[:8]}",
                        'entity_id': entity.id,
                        'content': obs.content,
                        'created_at': datetime.now(UTC)
                    })
            except Exception as e:
                print(f"Warning: Failed to reindex observations for {entity_file}: {str(e)}")
