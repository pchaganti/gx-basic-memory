"""Service for orchestrating entity, relation, and observation operations."""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

from basic_memory.schemas import Entity, Observation, Relation
from basic_memory.fileio import write_entity_file, read_entity_file, delete_entity_file
from basic_memory.services import EntityService, RelationService, ObservationService

class MemoryService:
    """Orchestrates entity, relation, and observation operations with filesystem handling."""
    
    def __init__(
        self,
        project_path: Optional[Path],
        entity_service: EntityService,
        relation_service: RelationService,
        observation_service: ObservationService
    ):
        self.project_path = project_path
        self.entities_path = project_path / "entities" if project_path else None
        self.entity_service = entity_service
        self.relation_service = relation_service
        self.observation_service = observation_service

    async def create_entities(self, entities_data: List[Dict[str, Any]]) -> List[Entity]:
        """Create multiple entities with their observations."""
        entities = [Entity.model_validate(data) for data in entities_data]

        # Write files in parallel (filesystem is source of truth)
        async def write_file(entity: Entity):
            await write_entity_file(self.entities_path, entity)

        file_writes = [write_file(entity) for entity in entities]
        await asyncio.gather(*file_writes)

        # Update database index sequentially
        for entity in entities:
            await self.entity_service.create_entity(entity)

        return entities

    async def create_relations(self, relations_data: List[Dict[str, Any]]) -> List[Relation]:
        """Create multiple relations between entities."""
        relations = [Relation.model_validate(data) for data in relations_data]

        for relation in relations:
            # First read complete entities from filesystem
            from_entity = await read_entity_file(self.entities_path, relation.from_id) 
            to_entity = await read_entity_file(self.entities_path, relation.to_id)

            # Add the new relation to the source entity
            if not hasattr(from_entity, 'relations'):
                from_entity.relations = []
            from_entity.relations.append(relation)

            # Write updated entity files (filesystem is source of truth)
            await asyncio.gather(
                write_entity_file(self.entities_path, from_entity),
                write_entity_file(self.entities_path, to_entity)
            )

            # Now update the database index
            await self.relation_service.create_relation(relation)

        return relations

    async def add_observations(self, observations_data: List[Dict[str, Any]]) -> None:
        """Add observations to existing entities."""
        # First read all entities and create their observations
        entity_updates = []
        for data in observations_data:
            entity = await read_entity_file(self.entities_path, data["entityName"])
            new_observations = [Observation(content=content) for content in data["contents"]]
            entity.observations.extend(new_observations)
            entity_updates.append(entity)

        # Write updated entities in parallel
        async def write_file(entity: Entity):
            await write_entity_file(self.entities_path, entity)

        file_writes = [write_file(entity) for entity in entity_updates]
        await asyncio.gather(*file_writes)

        # Update database indexes sequentially
        for entity in entity_updates:
            await self.entity_service.rebuild_index(entity)

    async def delete_entities(self, entity_names: List[str]) -> None:
        """Delete multiple entities and their associated data."""
        # First get all entities to be deleted
        entities = []
        for name in entity_names:
            entity = await self.entity_service.get_by_name(name)
            entities.append(entity)

        # Delete files in parallel
        async def delete_file(entity: Entity):
            await delete_entity_file(self.entities_path, entity.id)

        file_deletes = [delete_file(entity) for entity in entities]
        await asyncio.gather(*file_deletes)

        # Update database sequentially
        for entity in entities:
            await self.entity_service.delete_entity(entity.id)

    async def delete_observations(self, deletions: List[Dict[str, Any]]) -> None:
        """Delete specific observations from entities."""
        # First read and update all entities
        entity_updates = []
        for deletion in deletions:
            entity = await read_entity_file(self.entities_path, deletion["entityName"])
            entity.observations = [
                obs for obs in entity.observations
                if obs.content not in deletion["observations"]
            ]
            entity_updates.append(entity)

        # Write updated entities in parallel
        async def write_file(entity: Entity):
            await write_entity_file(self.entities_path, entity)

        file_writes = [write_file(entity) for entity in entity_updates]
        await asyncio.gather(*file_writes)

        # Update database indexes sequentially
        for entity in entity_updates:
            await self.entity_service.rebuild_index(entity)

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> None:
        """Delete specific relations between entities."""
        # First get all entities and delete relations
        updates = []
        for data in relations:
            from_entity = await self.entity_service.get_by_name(data["from"])
            to_entity = await self.entity_service.get_by_name(data["to"])
            await self.relation_service.delete_relation(from_entity, to_entity, data["relationType"])
            updates.append(from_entity)

        # Write updated files in parallel
        async def write_file(entity: Entity):
            await write_entity_file(self.entities_path, entity)

        file_writes = [write_file(entity) for entity in updates]
        await asyncio.gather(*file_writes)

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
        async def read_node(name: str) -> Optional[Entity]:
            if entity := await read_entity_file(self.entities_path, name):
                return entity
            return None

        entities = [entity for entity in await asyncio.gather(*(read_node(name) for name in names))
                   if entity is not None]

        return {
            "entities": [entity.model_dump() for entity in entities]
            # Relations between these entities are included in model_dump()
        }