from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from uuid import uuid4
import shutil

from sqlalchemy.ext.asyncio import AsyncSession
from basic_memory.db import get_sessionmaker
from basic_memory.models import Entity, Observation, Relation
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository

class MemoryServiceError(Exception):
    """Base exception for memory service errors"""
    pass

class FileOperationError(MemoryServiceError):
    """Raised when file operations fail"""
    pass

class DatabaseSyncError(MemoryServiceError):
    """Raised when database sync fails - indicates reindex may be needed"""
    pass

class EntityNotFoundError(MemoryServiceError):
    """Raised when an entity cannot be found in the filesystem"""
    pass

class MemoryService:
    """
    Core service layer for basic-memory.
    
    Implementation follows "filesystem is source of truth" principle:
    1. Write to filesystem first
    2. Update database indexes second
    3. Database is treated as disposable/rebuild-able index
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.session_maker = get_sessionmaker()
        self.project_path = Path.home() / ".basic-memory" / "projects" / project_name
        
    async def initialize_project(self):
        """
        Initialize project directory structure.
        Called when creating a new project or ensuring structure exists.
        """
        try:
            (self.project_path / "entities").mkdir(parents=True, exist_ok=True)
            # Add other directories as needed (e.g., for attachments)
        except Exception as e:
            raise FileOperationError(f"Failed to initialize project structure: {str(e)}") from e

    async def _get_repos(self) -> Tuple[EntityRepository, ObservationRepository, RelationRepository]:
        """Get repository instances with a shared session"""
        session = self.session_maker()
        try:
            return (
                EntityRepository(session, Entity),
                ObservationRepository(session, Observation),
                RelationRepository(session, Relation)
            )
        except:
            await session.close()
            raise
            
    @staticmethod
    def _generate_id(name: str) -> str:
        """Generate timestamp-based ID for an entity"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d")
        normalized_name = name.lower().replace(" ", "-")
        return f"{timestamp}-{normalized_name}-{uuid4().hex[:8]}"

    async def _write_entity_file(self, entity_data: dict) -> bool:
        """Write entity to filesystem in Markdown format."""
        try:
            entity_path = self.project_path / "entities" / f"{entity_data['id']}.md"
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
            entity_path = self.project_path / "entities" / f"{entity_id}.md"
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
        """Update database index with entity data using upsert pattern."""
        entity_repo, _, _ = await self._get_repos()
        
        try:
            # TODO: Implement proper upsert logic
            try:
                return await entity_repo.create(entity_data)
            except:
                existing = await entity_repo.find_by_id(entity_data['id'])
                if existing:
                    return await entity_repo.update(entity_data['id'], entity_data)
                raise
        except Exception as e:
            raise DatabaseSyncError(f"Failed to update database index: {str(e)}") from e

    async def create_entity(self, name: str, type: str, description: Optional[str] = None) -> Entity:
        """Create a new entity."""
        entity_id = self._generate_id(name)
        entity_data = {
            "id": entity_id,
            "name": name,
            "entity_type": type,
            "description": description,
            "created_at": datetime.now(UTC)
        }
        
        # Step 1: Write to filesystem (source of truth)
        await self._write_entity_file(entity_data)
        
        # Step 2: Update database index (can be rebuilt if needed)
        try:
            return await self._update_db_index(entity_data)
        except DatabaseSyncError as e:
            print(f"Warning: Database sync failed, reindex may be needed: {str(e)}")
            return Entity(**entity_data)

    async def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID, reading from filesystem first."""
        # Read from filesystem (source of truth)
        entity_data = await self._read_entity_file(entity_id)
        
        # Try to get from database for full object
        try:
            entity_repo, _, _ = await self._get_repos()
            entity = await entity_repo.find_by_id(entity_id)
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
            entity_path = self.project_path / "entities" / f"{entity_id}.md"
            if entity_path.exists():
                entity_path.unlink()
            
            # Try to delete from database, but don't error if it fails
            try:
                entity_repo, _, _ = await self._get_repos()
                await entity_repo.delete(entity_id)
            except DatabaseSyncError:
                pass  # Database cleanup can happen during reindex
                
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to delete entity: {str(e)}") from e

    async def rebuild_index(self) -> None:
        """Rebuild database index from filesystem contents."""
        try:
            entities_dir = self.project_path / "entities"
            if not entities_dir.exists():
                return
                
            for entity_file in entities_dir.glob("*.md"):
                try:
                    entity_data = await self._read_entity_file(entity_file.stem)
                    await self._update_db_index(entity_data)
                except Exception as e:
                    print(f"Warning: Failed to reindex {entity_file}: {str(e)}")
        except Exception as e:
            raise DatabaseSyncError(f"Failed to rebuild index: {str(e)}") from e

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Implementation depends on what needs cleanup
        pass