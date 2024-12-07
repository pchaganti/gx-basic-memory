"""Service for orchestrating entity, relation, and observation operations."""
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..schemas import Entity, EntityCreate, Relation, RelationCreate, Observation
from ..fileio import write_entity_file, read_entity_file, delete_entity_file
from .entity_service import EntityService
from .relation_service import RelationService

class MemoryService:
    """Orchestrates entity, relation, and observation operations with filesystem handling."""
    
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path
        self.entities_path = project_path / "entities" if project_path else None
        # Initialize with repos when we add them
        self.entity_service = EntityService()
        self.relation_service = RelationService()

    async def create_entities(self, entities_data: List[Dict[str, Any]]) -> List[Entity]:
        """Create multiple entities with their observations."""
        async def create_and_write(data: Dict[str, Any]) -> Entity:
            create_data = EntityCreate.model_validate(data)
            entity = await self.entity_service.create_entity(create_data)
            await write_entity_file(self.entities_path, entity)
            return entity
            
        return [await create_and_write(data) for data in entities_data]

    async def create_relations(self, relations_data: List[Dict[str, Any]]) -> List[Relation]:
        """Create multiple relations between entities."""
        async def create_and_write_relation(data: Dict[str, Any]) -> Relation:
            create_data = RelationCreate.model_validate(data)
            
            # Get the actual entities
            from_entity = await self.entity_service.get_by_name(create_data.from_)
            to_entity = await self.entity_service.get_by_name(create_data.to)
            
            # Create relation
            relation = await self.relation_service.create_relation(
                create_data=create_data,
                from_entity=from_entity,
                to_entity=to_entity
            )
            
            # Write updated from_entity to file
            await write_entity_file(self.entities_path, from_entity)
            return relation
            
        return [await create_and_write_relation(data) for data in relations_data]