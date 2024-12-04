from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import IntegrityError

from basic_memory.models import Entity as DbEntity  # Rename to avoid confusion
from basic_memory.repository import EntityRepository
from basic_memory.schemas import Entity, Observation


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
    
    def __init__(self, project_path: Path, entity_repo: EntityRepository):
        self.project_path = project_path
        self.entity_repo = entity_repo
        self.entities_path = project_path / "entities"

    async def _write_entity_file(self, entity: Entity) -> bool:
        """Write entity to filesystem in markdown format."""
        try:
            entity_path = self.entities_path / f"{entity.id}.md"
            entity_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Format entity data as markdown
            content = [
                f"# {entity.name}\n",
                f"type: {entity.entity_type}\n",
                "\n",  # Observations section
                "## Observations\n",
            ]

            # Add observations
            for obs in entity.observations:
                content.append(f"- {obs.content}\n")
            
            # Write to temp file first, then rename for atomic operation
            temp_path = entity_path.with_suffix('.tmp')
            temp_path.write_text("".join(content))
            temp_path.rename(entity_path)
            
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to write entity file: {str(e)}") from e

    async def _read_entity_file(self, entity_id: str) -> Entity:
        """Read entity data from filesystem."""
        try:
            entity_path = self.entities_path / f"{entity_id}.md"
            if not entity_path.exists():
                raise EntityNotFoundError(f"Entity file not found: {entity_id}")
            
            content = entity_path.read_text().split("\n")
            
            # Parse markdown content
            # First line should be "# Name"
            name = content[0].lstrip("# ").strip()
            
            # Parse metadata (type)
            entity_type = ""
            observations = []
            
            # Parse content sections
            in_observations = False
            for line in content[1:]:  # Skip the title line
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("type: "):
                    entity_type = line.replace("type: ", "").strip()
                elif line == "## Observations":
                    in_observations = True
                elif in_observations and line.startswith("- "):
                    observations.append(Observation(content=line[2:]))
            
            return Entity(
                id=entity_id,
                name=name,
                entity_type=entity_type,
                observations=observations
            )
            
        except EntityNotFoundError:
            raise
        except Exception as e:
            raise FileOperationError(f"Failed to read entity file: {str(e)}") from e

    async def _update_db_index(self, entity: Entity) -> DbEntity:
        """Update database index with entity data."""
        try:
            # Convert Pydantic Entity to dict for DB
            entity_data = {
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": "\n".join(obs.content for obs in entity.observations),
                "references": "",  # We might want to handle references differently later
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            # Try to find existing entity first
            existing = await self.entity_repo.find_by_id(entity.id)
            
            if existing:
                # Update existing entity
                await self.entity_repo.session.refresh(existing)
                for key, value in entity_data.items():
                    setattr(existing, key, value)
                await self.entity_repo.session.commit()
                return existing
            else:
                # Create new entity
                db_entity = await self.entity_repo.create(entity_data)
                await self.entity_repo.session.commit()
                return db_entity
                
        except IntegrityError as e:
            await self.entity_repo.session.rollback()
            raise DatabaseSyncError(f"Failed to update database index: {str(e)}") from e
        except Exception as e:
            await self.entity_repo.session.rollback()
            raise DatabaseSyncError(f"Failed to update database index: {str(e)}") from e

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
        await self._write_entity_file(entity)
        
        # Step 2: Update database index (can be rebuilt if needed)
        try:
            await self._update_db_index(entity)
        except DatabaseSyncError:
            pass  # Return entity from file even if DB fails
            
        return entity

    async def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID, reading from filesystem first."""
        # Read from filesystem (source of truth)
        entity = await self._read_entity_file(entity_id)
        
        # Try to update database index if needed
        try:
            await self._update_db_index(entity)
        except DatabaseSyncError:
            pass  # Return entity from file even if DB fails
            
        return entity

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
                await self.entity_repo.session.commit()
            except DatabaseSyncError:
                await self.entity_repo.session.rollback()
                pass  # Database cleanup can happen during reindex
                
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to delete entity: {str(e)}") from e

    async def rebuild_index(self) -> None:
        """Rebuild database index from filesystem contents."""
        try:
            if not self.entities_path.exists():
                return
                
            for entity_file in self.entities_path.glob("*.md"):
                try:
                    entity = await self._read_entity_file(entity_file.stem)
                    await self._update_db_index(entity)
                except Exception as e:
                    print(f"Warning: Failed to reindex {entity_file}: {str(e)}")
        except Exception as e:
            raise DatabaseSyncError(f"Failed to rebuild index: {str(e)}") from e