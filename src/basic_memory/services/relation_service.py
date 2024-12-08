"""Service for managing relations in the database."""
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import delete

from basic_memory.models import Relation as DbRelation, Relation
from basic_memory.repository import RelationRepository
from basic_memory.schemas import EntityIn, RelationIn
from . import ServiceError, DatabaseSyncError, RelationError


class RelationService:
    """
    Service for managing relations in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, relation_repo: RelationRepository):
        self.project_path = project_path
        self.relation_repo = relation_repo

    async def create_relation(self, relation: RelationIn) -> Relation:
        """Create a new relation in the database."""
        try:
            db_data = relation.model_dump()
            db_data['created_at'] = datetime.now(UTC)
            return await self.relation_repo.create(db_data)
        except Exception as e:
            raise DatabaseSyncError(f"Failed to sync relation to database: {str(e)}") from e

    async def delete_relation(self, from_entity: EntityIn, to_entity: EntityIn, relation_type: str) -> bool:
        """Delete a specific relation between entities."""
        # Find and remove the relation from the entity's relations
        if hasattr(from_entity, 'relations'):
            from_entity.relations = [
                r for r in from_entity.relations 
                if not (r.to_id == to_entity.id and r.relation_type == relation_type)
            ]
        
        # Remove from database index
        await self.relation_repo.execute_query(
            delete(DbRelation).where(
                (DbRelation.from_id == from_entity.id) &
                (DbRelation.to_id == to_entity.id) &
                (DbRelation.relation_type == relation_type)
            )
        )
        return True