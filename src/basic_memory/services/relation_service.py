"""Service for managing relations between entities."""
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List
from sqlalchemy import delete

from basic_memory.models import Relation as DbRelation
from basic_memory.repository import RelationRepository
from basic_memory.schemas import Entity, Relation
from basic_memory.fileio import (
    write_entity_file, read_entity_file,
    FileOperationError
)
from . import ServiceError, DatabaseSyncError, RelationError


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
        Get all relations for an entity (outgoing relations).
        
        Args:
            entity: Entity to get relations for
            
        Returns:
            List of relations where the entity is the source
        """
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
