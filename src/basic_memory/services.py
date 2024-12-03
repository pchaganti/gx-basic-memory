from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from basic_memory.models import Entity
from basic_memory.repository import EntityRepository

class ServiceError(Exception):
    """Base exception for service errors"""
    pass

class FileOperationError(ServiceError):
    """Raised when file operations fail"""
    pass

class DatabaseSyncError(ServiceError):
    """Raised when database sync fails"""
    pass

class EntityNotFoundError(ServiceError):
    """Raised when an entity cannot be found"""
    pass

class EntityService:
    """
    Service for managing entities in the filesystem and database.
    Follows the "filesystem is source of truth" principle.
    """
    
    def __init__(self, project_path: Path, session: AsyncSession):
        self.project_path = project_path
        self.entity_repo = EntityRepository(session, Entity)
        self.entities_path = project_path / "entities"

    @staticmethod
    def _generate_id(name: str) -> str:
        """Generate timestamp-based ID for an entity"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d")
        normalized_name = name.lower().replace(" ", "-")
        return f"{timestamp}-{normalized_name}-{uuid4().hex[:8]}"

    async def _write_entity_file(self, entity_data: dict) -> bool:
        """Write entity to filesystem in markdown format."""
        try:
            entity_path = self.entities_path / f"{entity_data['id']}.md"
            entity_path.parent.mkdir(parents=True, exist_ok=True)
            
            # TODO: Replace with actual markdown formatting
            content = f"# {entity_data['name']}\n\nStub content"
            
            # Write to temp file first, then rename for atomic operation
            temp_path = entity_path.with_suffix('.tmp')
            temp_path.write_text(content)
            temp_path.rename(entity_path)
            
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to write entity file: {str(e)}") from e

    async def _read_entity_file(self, entity_id: str) -> Dict:
        """Read entity data from filesystem."""
        try:
            entity_path = self.entities_path / f"{entity_id}.md"
            if not entity_path.exists():
                raise EntityNotFoundError(f"Entity file not found: {entity_id}")
            
            # TODO: Implement actual markdown parsing
            content = entity_path.read_text()
            # Stub parsing
            return {"id": entity_id, "content": content}
        except EntityNotFoundError:
            raise
        except Exception as e:
            raise FileOperationError(f"Failed to read entity file: {str(e)}") from e

    async def _update_db_index(self, entity_data: dict) -> Entity:
        """Update database index with entity data."""
        try:
            # TODO: Implement proper upsert logic
            try:
                return await self.entity_repo.create(entity_data)
            except:
                existing = await self.entity_repo.find_by_id(entity_data['id'])
                if existing:
                    return await self.entity_repo.update(entity_data['id'], entity_data)
                raise
        except Exception as e:
            raise DatabaseSyncError(f"Failed to update database index: {str(e)}") from e

    async def create_entity(self, name: str, type: str, description: str = "") -> Entity:
        """Create a new entity."""
        entity_id = self._generate_id(name)
        entity_data = {
            "id": entity_id,
            "name": name,
            "entity_type": type,
            "description": description,
            "references": "",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        # Step 1: Write to filesystem (source of truth)
        await self._write_entity_file(entity_data)
        
        # Step 2: Update database index (can be rebuilt if needed)
        try:
            return await self._update_db_index(entity_data)
        except DatabaseSyncError as e:
            # Return entity from file data if DB fails
            return Entity(**entity_data)

    async def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID, reading from filesystem first."""
        # Read from filesystem (source of truth)
        entity_data = await self._read_entity_file(entity_id)
        
        # Try to get from database for full object
        try:
            entity = await self.entity_repo.find_by_id(entity_id)
            if entity is None:
                # Reindex this entity if not in database
                entity = await self._update_db_index(entity_data)
            return entity
        except DatabaseSyncError:
            # Return basic entity from file data if DB fails
            return Entity(**entity_data)

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from filesystem and database."""
        try:
            # Delete from filesystem first
            entity_path = self.entities_path / f"{entity_id}.md"
            if entity_path.exists():
                entity_path.unlink()
            
            # Try to delete from database, but don't error if it fails
            try:
                await self.entity_repo.delete(entity_id)
            except DatabaseSyncError:
                pass  # Database cleanup can happen during reindex
                
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to delete entity: {str(e)}") from e

    async def rebuild_index(self) -> None:
        """Rebuild database index for entities from filesystem contents."""
        try:
            if not self.entities_path.exists():
                return
                
            for entity_file in self.entities_path.glob("*.md"):
                try:
                    entity_data = await self._read_entity_file(entity_file.stem)
                    await self._update_db_index(entity_data)
                except Exception as e:
                    print(f"Warning: Failed to reindex {entity_file}: {str(e)}")
        except Exception as e:
            raise DatabaseSyncError(f"Failed to rebuild index: {str(e)}") from e
