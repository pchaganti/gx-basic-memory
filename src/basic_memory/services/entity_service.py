"""Service for managing entities in both filesystem and database."""
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from basic_memory.models import Entity as DbEntity
from basic_memory.repository import EntityRepository
from basic_memory.schemas import Entity, Observation
from basic_memory.fileio import (
    read_entity_file, write_entity_file, delete_entity_file,
    FileOperationError
)
from . import ServiceError, DatabaseSyncError


class EntityService:
    """
    Service for managing entities in the filesystem and database.
    Follows the "filesystem is source of truth" principle.
    """
    
    def __init__(self, project_path: Path, entity_repo: EntityRepository):
        self.project_path = project_path
        self.entity_repo = entity_repo
        self.entities_path = project_path / "entities"

    async def _update_db_index(self, entity: Entity) -> DbEntity:
        """Update database index with entity data."""
        entity_data = {
            **entity.model_dump(),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        # Remove fields handled by other services
        entity_data.pop('observations', None)
        entity_data.pop('relations', None)
        
        # Try to find existing entity first
        if await self.entity_repo.find_by_id(entity.id):
            return await self.entity_repo.update(entity.id, entity_data)
        else:
            return await self.entity_repo.create(entity_data)

    async def create_entity(self, name: str, entity_type: str, 
                          observations: Optional[list[str]] = None) -> Entity:
        """Create a new entity."""
        # Convert string observations to Observation objects if provided
        obs_list = [Observation(content=obs) for obs in (observations or [])]
        
        # Create entity (ID will be auto-generated)
        entity = Entity(
            name=name,
            entity_type=entity_type,
            observations=obs_list
        )
        
        # Step 1: Write to filesystem (source of truth)
        await write_entity_file(self.entities_path, entity)
        
        # Step 2: Update database index
        await self._update_db_index(entity)
            
        return entity

    async def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID, reading from filesystem first."""
        # Read from filesystem (source of truth)
        entity = await read_entity_file(self.entities_path, entity_id)
        
        # Update database index
        await self._update_db_index(entity)
            
        return entity

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from filesystem and database."""
        # Delete from filesystem first (source of truth)
        await delete_entity_file(self.entities_path, entity_id)
        
        # Delete from database index
        await self.entity_repo.delete(entity_id)
        return True

    async def rebuild_index(self) -> None:
        """Rebuild database index from filesystem contents."""
        if not self.entities_path.exists():
            return
            
        try:
            entity_files = list(self.entities_path.glob("*.md"))
        except Exception as e:
            raise FileOperationError(f"Failed to read entities directory: {str(e)}") from e
                
        for entity_file in entity_files:
            try:
                entity = await read_entity_file(self.entities_path, entity_file.stem)
                await self._update_db_index(entity)
            except Exception as e:
                print(f"Warning: Failed to reindex {entity_file}: {str(e)}")
