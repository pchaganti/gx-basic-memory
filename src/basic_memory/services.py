from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import and_, select, delete

from basic_memory.models import Entity as DbEntity  # Rename to avoid confusion
from basic_memory.models import Observation as DbObservation
from basic_memory.models import Relation as DbRelation
from basic_memory.repository import EntityRepository, ObservationRepository, RelationRepository
from basic_memory.schemas import Entity, Observation, Relation
from basic_memory.fileio import (
    read_entity_file, write_entity_file, delete_entity_file,
    FileOperationError, EntityNotFoundError
)


class ServiceError(Exception):
    """Base exception for service errors"""
    pass


class DatabaseSyncError(ServiceError):
    """Raised when database sync fails"""
    pass


class RelationError(ServiceError):
    """Base exception for relation-specific errors"""
    pass


class EntityService:
    """Service for managing entities in the filesystem and database."""
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
        
        # Observations will be handled by ObservationService
        entity_data.pop('observations', None)  # Remove observations if present
        entity_data.pop('relations', None)     # Remove relations if present
        
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


class ObservationService:
    """Service for managing observations in the filesystem and database."""
    def __init__(self, project_path: Path, observation_repo: ObservationRepository):
        self.project_path = project_path
        self.entities_path = project_path / "entities"
        self.observation_repo = observation_repo
        
    async def add_observation(self, entity: Entity, content: str, 
                          context: Optional[str] = None) -> Observation:
        """Add a new observation to an entity."""
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


class RelationService:
    """
    Service for managing relations between entities.
    Follows the "filesystem is source of truth" principle.
    
    Relations are stored in entity markdown files and indexed in the database
    for efficient querying.
    """
    
    def __init__(self, project_path: Path, relation_repo: RelationRepository):
        self.project_path = project_path
        self.entities_path = project_path / "entities"
        self.relation_repo = relation_repo
    
    async def create_relation(self, from_entity: Entity, to_entity: Entity, relation_type: str,
                          context: Optional[str] = None) -> Relation:
        """
        Create a new relation between two entities.
        
        Args:
            from_entity: Source entity
            to_entity: Target entity
            relation_type: Type of relation
            context: Optional context for the relation
            
        Returns:
            The created Relation
            
        Raises:
            FileOperationError: If file operations fail
            DatabaseSyncError: If database sync fails
        """
        # Create new relation with actual Entity objects
        relation = Relation(
            from_entity=from_entity,
            to_entity=to_entity,
            relation_type=relation_type,
            context=context
        )
        
        # Add relation to source entity's relations list
        if not hasattr(from_entity, 'relations'):
            from_entity.relations = []
        from_entity.relations.append(relation)
        
        # Update filesystem first (source of truth)
        await write_entity_file(self.entities_path, from_entity)
        
        # Update database index
        # model_dump will handle converting Entity refs to IDs
        try:
            db_data = relation.model_dump()
            db_data['created_at'] = datetime.now(UTC)
            await self.relation_repo.create(db_data)
            return relation
        except Exception as e:
            raise DatabaseSyncError(f"Failed to sync relation to database: {str(e)}") from e

    async def get_entity_relations(self, entity: Entity) -> List[Relation]:
        """
        Get all relations for an entity (both outgoing and incoming).
        
        Args:
            entity: Entity to get relations for
            
        Returns:
            List of relations where the entity is either source or target
        """
        # Relations are stored in the entity object
        return getattr(entity, 'relations', [])

    async def delete_relation(self, from_entity: Entity, relation_id: str) -> bool:
        """
        Delete a relation from both filesystem and database.
        
        Args:
            from_entity: Source entity containing the relation
            relation_id: ID of the relation to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            RelationError: If relation cannot be found or deleted
        """
        # Remove relation from entity's relations
        if hasattr(from_entity, 'relations'):
            from_entity.relations = [
                r for r in from_entity.relations 
                if r.id != relation_id
            ]
            
        # Update filesystem first (source of truth)
        await write_entity_file(self.entities_path, from_entity)
        
        # Remove from database index
        await self.relation_repo.delete(relation_id)
        return True

    async def rebuild_relation_index(self) -> None:
        """
        Rebuild the relation database index from filesystem contents.
        Used for recovery or ensuring sync.
        """
        if not self.entities_path.exists():
            return
            
        try:
            entity_files = list(self.entities_path.glob("*.md"))
        except Exception as e:
            raise FileOperationError(f"Failed to read entities directory: {str(e)}") from e
        
        # Clear existing relation index
        await self.relation_repo.execute_query(delete(DbRelation))
        
        # Rebuild from each entity file
        for entity_file in entity_files:
            try:
                entity = await read_entity_file(self.entities_path, entity_file.stem)
                for relation in getattr(entity, 'relations', []):
                    db_data = relation.model_dump()
                    db_data['created_at'] = datetime.now(UTC)
                    await self.relation_repo.create(db_data)
            except Exception as e:
                print(f"Warning: Failed to reindex relations for {entity_file}: {str(e)}")
