"""Service for managing relations in the database."""
from pathlib import Path
from typing import List, Dict, Any

from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.schemas import Entity, Relation
from . import DatabaseSyncError
from basic_memory.models import Relation as RelationModel

class RelationService:
    """
    Service for managing relations in the database.
    File operations are handled by MemoryService.
    """
    
    def __init__(self, project_path: Path, relation_repo: RelationRepository):
        self.project_path = project_path
        self.relation_repo = relation_repo

    async def create_relation(self, relation: Relation) -> RelationModel:
        """Create a new relation in the database."""
        try:
            return await self.relation_repo.create(relation.model_dump())
        except Exception as e:
            raise DatabaseSyncError(f"Failed to sync relation to database: {str(e)}") from e

    async def delete_relation(self, from_entity: Entity, to_entity: Entity, relation_type: str) -> bool:
        """Delete a specific relation between entities."""
        try:
            # Use repository to find and delete the relation
            filters = {
                'from_id': from_entity.id,
                'to_id': to_entity.id,
                'relation_type': relation_type
            }
            
            # Delete in database
            result = await self.relation_repo.delete_by_fields(**filters)
            
            # Update in-memory relations if present
            if hasattr(from_entity, 'relations'):
                from_entity.relations = [
                    r for r in from_entity.relations 
                    if not (r.to_id == to_entity.id and r.relation_type == relation_type)
                ]
            
            return result
            
        except Exception as e:
            raise DatabaseSyncError(f"Failed to delete relation: {str(e)}") from e

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> bool:
        """
        Delete relations matching specified criteria.
        
        Args:
            relations: List of dicts with from_id, to_id, and optional relation_type
            
        Returns:
            True if any relations were deleted
        """
        try:
            deleted = False
            for relation in relations:
                filters = {
                    'from_id': relation['from_id'],
                    'to_id': relation['to_id']
                }
                if 'relation_type' in relation:
                    filters['relation_type'] = relation['relation_type']
                    
                result = await self.relation_repo.delete_by_fields(**filters)
                if result:
                    deleted = True
                    
            return deleted
        except Exception as e:
            raise DatabaseSyncError(f"Failed to delete relations: {str(e)}") from e