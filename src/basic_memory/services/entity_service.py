"""Service for managing entities in the database."""
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from basic_memory.models import Entity as DbEntity
from basic_memory.repository import EntityRepository
from basic_memory.schemas import Entity, EntityCreate
from . import ServiceError, DatabaseSyncError

class EntityService:
    """
    Service for managing entities in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, entity_repo: EntityRepository):
        self.project_path = project_path
        self.entity_repo = entity_repo

    async def create_entity(self, create_data: EntityCreate) -> Entity:
        """Create a new entity in the database."""
        # Create Entity from EntityCreate data
        entity = Entity.from_create(create_data)
        
        # Create DB record
        db_data = {
            **entity.model_dump(),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        await self.entity_repo.create(db_data)
        
        return entity

    async def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID."""
        db_entity = await self.entity_repo.find_by_id(entity_id)
        if not db_entity:
            raise ServiceError(f"Entity not found: {entity_id}")
            
        return Entity(
            id=db_entity.id,
            name=db_entity.name,
            entity_type=db_entity.entity_type
        )

    async def get_by_name(self, name: str) -> Entity:
        """Get entity by name."""
        db_entity = await self.entity_repo.find_by_name(name)
        if not db_entity:
            raise ServiceError(f"Entity not found: {name}")
            
        return Entity(
            id=db_entity.id,
            name=db_entity.name,
            entity_type=db_entity.entity_type
        )

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from database."""
        await self.entity_repo.delete(entity_id)
        return True