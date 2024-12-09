"""Service for orchestrating entity, relation, and observation operations."""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

from basic_memory.models import Entity, Observation
from basic_memory.schemas import (
    ObservationsIn, EntityIn, RelationIn
)
from basic_memory.fileio import write_entity_file, read_entity_file
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

    async def create_entities(self, entities_in: List[EntityIn]) -> List[Entity]:
        """Create multiple entities with their observations."""

        # Write files in parallel (filesystem is source of truth)
        async def write_file(entity: EntityIn):
            await write_entity_file(self.entities_path, entity)

        file_writes = [write_file(entity) for entity in entities_in]
        await asyncio.gather(*file_writes)

        async def create_entity_in_db(entity_in: EntityIn):
            await self.entity_service.create_entity(entity_in)
            await self.observation_service.add_observations(entity_in, entity_in.observations)
            [await self.relation_service.create_relation(relation_in) for relation_in in entity_in.relations]
            # query the entity again to return relations
            final_entity = await self.entity_service.get_entity(entity_in.id)
            return final_entity

        # Update database index sequentially
        entities = [await create_entity_in_db(entities_in) for entities_in in entities_in]
        return entities

    async def create_relations(self, relations_data: List[Dict[str, Any]]) -> List[RelationIn]:
        """Create multiple relations between entities."""
        relations = [RelationIn.model_validate(data) for data in relations_data]

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

    async def add_observations(self, observations_in: ObservationsIn) -> List[Observation]:
        """Add observations to an existing entity.
        
        Args:
            observations_in: input containing entity_id and observations
            
        Returns:
            List[Observation] with the newly created observations
        """
        # First get the entity from DB to get its ID
        db_entity = await self.entity_service.get_entity(observations_in.entity_id)
        
        # Read entity from filesystem using the ID
        entity = await read_entity_file(self.entities_path, db_entity.id)

        # Create new observations for the entity
        for obs in observations_in.observations:
            entity.observations.append(obs)

        # Write updated entity file
        await write_entity_file(self.entities_path, entity)
        
        # Update database index
        added_observations = await self.observation_service.add_observations(entity, observations_in.observations)

        db_entity = await self.entity_service.get_entity(entity.id)
        return added_observations

    async def delete_entities(self, entity_names: List[str]) -> None:
       pass

    async def delete_observations(self, deletions: List[Dict[str, Any]]) -> None:
        pass

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> None:
        pass

    async def read_graph(self) -> List[Entity]:
        """Read the entire knowledge graph."""
        return await self.entity_service.get_all()

    async def search_nodes(self, query: str) -> List[Entity]:
        """Search for nodes in the knowledge graph."""
        return await self.entity_service.search(query)

    async def open_nodes(self, names: List[str]) -> List[Entity]:
        """Get specific nodes and their relationships."""
        async def read_node(name: str) -> Optional[Entity]:
            # Get ID from name first
            db_entity = await self.entity_service.get_entity(name)
            if db_entity:
                return await read_entity_file(self.entities_path, db_entity.id)
            return None

        entities = [entity for entity in await asyncio.gather(*(read_node(name) for name in names))
                   if entity is not None]
        return entities