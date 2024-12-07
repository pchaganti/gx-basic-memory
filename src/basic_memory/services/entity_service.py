"""Service for managing entities in the database."""
from datetime import datetime, UTC
from pathlib import Path

from basic_memory.repository import EntityRepository
from basic_memory.schemas import Entity
from basic_memory.models import Entity as EntityModel
from . import ServiceError

class EntityService:
    """
    Service for managing entities in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, entity_repo: EntityRepository):
        self.project_path = project_path
        self.entity_repo = entity_repo

    async def create_entity(self, entity: Entity) -> EntityModel:
        """Create a new entity in the database."""
        # Create DB record
        db_data = {
            **entity.model_dump(),
            "created_at": datetime.now(UTC),
        }
        return await self.entity_repo.create(db_data)

    async def get_entity(self, entity_id: str) -> EntityModel:
        """Get entity by ID."""
        db_entity = await self.entity_repo.find_by_id(entity_id)
        if not db_entity:
            raise ServiceError(f"Entity not found: {entity_id}")
            
        return db_entity

    # TODO name is not uniaue
    async def get_by_name(self, name: str) -> EntityModel:
        """Get entity by name."""
        db_entity = await self.entity_repo.find_by_name(name)
        if not db_entity:
            raise ServiceError(f"Entity not found: {name}")
            
        return db_entity

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from database."""
        return await self.entity_repo.delete(entity_id)