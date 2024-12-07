from typing import List, Dict, Any, Optional
from pathlib import Path

from ..schemas import Entity, Relation, Observation
from .entity_service import EntityService
from .relation_service import RelationService
from .observation_service import ObservationService

class MemoryService:
    """Orchestrates entity, relation, and observation operations."""
    
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path
        self.entity_service = EntityService()
        self.relation_service = RelationService()
        self.observation_service = ObservationService()

    async def create_entities(self, entities_data: List[Dict[str, Any]]) -> List[Entity]:
        """Create multiple entities with their observations."""
        results = []
        for data in entities_data:
            # Convert to Pydantic model for validation
            entity = Entity(
                name=data["name"],
                entity_type=data["entityType"]
            )
            
            # Create the entity
            created = await self.entity_service.create_entity(entity)
            
            # Add observations if any
            if observations := data.get("observations"):
                obs_models = [Observation(content=obs) for obs in observations]
                await self.observation_service.add_observations(created.id, obs_models)
                created.observations.extend(obs_models)
            
            results.append(created)
            
        return results

    async def create_relations(self, relations_data: List[Dict[str, Any]]) -> List[Relation]:
        """Create multiple relations between entities."""
        results = []
        for data in relations_data:
            # Get the entities
            from_entity = await self.entity_service.get_entity(data["from"])
            to_entity = await self.entity_service.get_by_name(data["to"])
            
            # Create relation
            relation = Relation(
                from_entity=from_entity,
                to_entity=to_entity,
                relation_type=data["relationType"]
            )
            created = await self.relation_service.create(relation)
            results.append(created)
            
        return results

    async def add_observations(self, observations_data: List[Dict[str, Any]]) -> None:
        """Add observations to existing entities."""
        for data in observations_data:
            entity = await self.entity_service.get_by_name(data["entityName"])
            observations = [Observation(content=content) for content in data["contents"]]
            await self.observation_service.add_observations(entity.id, observations)

    async def delete_entities(self, entity_names: List[str]) -> None:
        """Delete multiple entities and their associated data."""
        for name in entity_names:
            entity = await self.entity_service.get_by_name(name)
            await self.entity_service.delete(entity.id)

    async def delete_observations(self, deletions: List[Dict[str, Any]]) -> None:
        """Delete specific observations from entities."""
        for deletion in deletions:
            entity = await self.entity_service.get_by_name(deletion["entityName"])
            observations = [Observation(content=content) for content in deletion["observations"]]
            await self.observation_service.delete_observations(entity.id, observations)

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> None:
        """Delete specific relations between entities."""
        for data in relations:
            # Get the entities
            from_entity = await self.entity_service.get_by_name(data["from"])
            to_entity = await self.entity_service.get_by_name(data["to"])
            
            await self.relation_service.delete_relation(
                from_entity.id,
                to_entity.id,
                data["relationType"]
            )

    async def read_graph(self) -> Dict[str, Any]:
        """Read the entire knowledge graph."""
        entities = await self.entity_service.get_all()
        return {
            "entities": [entity.model_dump() for entity in entities]
            # Relations are included in entity.model_dump()
        }

    async def search_nodes(self, query: str) -> Dict[str, Any]:
        """Search for nodes in the knowledge graph."""
        results = await self.entity_service.search(query)
        return {
            "matches": [entity.model_dump() for entity in results],
            "query": query
        }

    async def open_nodes(self, names: List[str]) -> Dict[str, Any]:
        """Get specific nodes and their relationships."""
        entities = []
        for name in names:
            entity = await self.entity_service.get_by_name(name)
            if entity:
                entities.append(entity)
        
        return {
            "entities": [entity.model_dump() for entity in entities]
            # Relations between these entities are included in model_dump()
        }