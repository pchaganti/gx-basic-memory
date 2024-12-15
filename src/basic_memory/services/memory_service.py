"""Service for orchestrating entity, relation, and observation operations."""
import asyncio
from typing import List, Dict, Any, Optional, Sequence
from pathlib import Path

from basic_memory.models import Entity, Observation, Relation
from basic_memory.schemas import (
    ObservationsIn, EntityIn, RelationIn
)
from basic_memory.fileio import write_entity_file, read_entity_file, EntityNotFoundError
from basic_memory.services import EntityService, RelationService, ObservationService
from loguru import logger


class MemoryService:
    """Orchestrates entity, relation, and observation operations with filesystem handling."""
    
    def __init__(
        self,
        project_path: Optional[Path],
        entity_service: EntityService,
        relation_service: RelationService,
        observation_service: ObservationService
    ):
        if project_path:
            assert project_path.is_dir(), "Path does not exist or is not a directory: {project_path}"
            self.project_path = project_path
            self.entities_path = project_path / "entities"

        self.entity_service = entity_service
        self.relation_service = relation_service
        self.observation_service = observation_service
        logger.debug(f"Initialized MemoryService with path: {project_path}")

    async def create_entities(self, entities_in: List[EntityIn]) -> List[Entity]:
        """Create multiple entities with their observations."""
        logger.debug(f"Creating {len(entities_in)} entities")

        # Write files in parallel (filesystem is source of truth)
        async def write_file(entity: EntityIn):
            try:
                existing = await self.entity_service.get_by_type_and_name(
                    entity.entity_type,
                    entity.name
                )
                if existing:
                    raise ValueError(
                        f"Entity already exists: {entity.entity_type}/{entity.name}"
                    )
            except EntityNotFoundError:
                # Good - entity doesn't exist yet
                pass

            # Generate ID and write file
            entity_id = Entity.generate_id(entity.entity_type, entity.name)
            await write_entity_file(self.entities_path, entity_id, entity)

        file_writes = [write_file(entity) for entity in entities_in]
        logger.debug("Starting parallel file writes")
        await asyncio.gather(*file_writes)
        logger.debug("Completed all file writes")

        async def create_entity_in_db(entity_in: EntityIn):
            logger.debug(f"Creating entity in DB: {entity_in}")
            try:
                # Create base entity
                created_entity = await self.entity_service.create_entity(entity_in)
                logger.debug(f"Created base entity: {created_entity.id}")

                # Add observations
                await self.observation_service.add_observations(created_entity.id, entity_in.observations)
                logger.debug(f"Added {len(entity_in.observations)} observations to {created_entity.id}")

                # Add relations
                for relation in entity_in.relations:
                    await self.relation_service.create_relation(relation)
                logger.debug(f"Added {len(entity_in.relations)} relations for {created_entity.id}")

                # Query final state
                final_entity = await self.entity_service.get_entity(created_entity.id)
                logger.debug(f"Retrieved final entity state: {final_entity}")
                return final_entity
            except Exception:
                logger.exception(f"Failed to create entity in DB: {entity_in}")
                raise

        # Update database index sequentially
        logger.debug("Starting DB updates")
        try:
            entities = []
            for entity_in in entities_in:
                entity = await create_entity_in_db(entity_in)
                entities.append(entity)
            logger.debug(f"Successfully created {len(entities)} entities in DB")
            return entities
        except Exception:
            # On failure, we should try to clean up any files we wrote
            logger.exception("Failed to create entities in DB")
            for entity in entities_in:
                try:
                    entity_id = Entity.generate_id(entity.entity_type, entity.name)
                    path = self.entities_path / entity_id
                    if path.exists():
                        path.unlink()
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up file for {entity.id}: {cleanup_error}")
            raise

    async def get_entity(self, entity_id: str):
        logger.debug(f"Get entity {entity_id} entities")
        entity = await self.entity_service.get_entity(entity_id)
        logger.debug(f"Found entity {entity}")
        return entity

    async def create_relations(self, relations_data: List[RelationIn]) -> List[Relation]:
        """Create multiple relations between entities."""
        logger.debug(f"Creating {len(relations_data)} relations")

        relations = []
        for relation in relations_data:
            logger.debug(f"Processing relation: {relation.from_id} -> {relation.to_id}")
            try:
                # First read complete entities from filesystem
                from_entity = await read_entity_file(self.entities_path, relation.from_id) 
                to_entity = await read_entity_file(self.entities_path, relation.to_id)
                logger.debug(f"Read entities for relation: {from_entity.id}, {to_entity.id}")

                # Add the new relation to the source entity
                if not hasattr(from_entity, 'relations'):
                    from_entity.relations = []
                from_entity.relations.append(relation)
                logger.debug(f"Added relation to source entity: {from_entity.id}")

                # Write updated entity files (filesystem is source of truth)
                logger.debug("Writing updated entity files")
                assert from_entity.id is not None
                assert to_entity.id is not None

                await asyncio.gather(
                    *[write_entity_file(self.entities_path, from_entity.id, from_entity),
                    write_entity_file(self.entities_path, to_entity.id, to_entity)]
                )
                logger.debug("Wrote updated entity files")

                # Now update the database index
                relation = await self.relation_service.create_relation(relation)
                relations.append(relation)
                logger.debug(f"Created relation in DB: {relation.id}")
            except Exception:
                logger.exception(f"Failed to create relation: {relation}")
                raise

        logger.debug(f"Successfully created {len(relations)} relations")
        return relations

    async def add_observations(self, observations_in: ObservationsIn) -> List[Observation]:
        """Add observations to an existing entity."""
        logger.debug(f"Adding observations to entity: {observations_in.entity_id}")
        try:
            # First get the entity from DB to get its ID
            db_entity = await self.entity_service.get_entity(observations_in.entity_id)
            logger.debug(f"Found entity in DB: {db_entity.id}")
            
            # Read entity from filesystem using the ID
            entity = await read_entity_file(self.entities_path, db_entity.id)
            logger.debug(f"Read entity from filesystem: {db_entity.id}")

            # Create new observations for the entity
            entity.observations += observations_in.observations
            logger.debug(f"Added {len(observations_in.observations)} observations to entity")

            # Write updated entity file
            logger.debug("Writing updated entity file")
            await write_entity_file(self.entities_path, db_entity.id, entity)
            logger.debug("Wrote updated entity file")
            
            # Update database index
            added_observations = await self.observation_service.add_observations(db_entity.id, observations_in.observations)
            logger.debug(f"Added {len(added_observations)} observations to DB")

            return added_observations
        except Exception:
            logger.exception(f"Failed to add observations to entity: {observations_in.entity_id}")
            raise

    async def delete_entities(self, entity_names: List[str]) -> None:
       pass

    async def delete_observations(self, deletions: List[Dict[str, Any]]) -> None:
        pass

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> None:
        pass

    async def read_graph(self) -> Sequence[Entity]:
        """Read the entire knowledge graph."""
        logger.debug("Reading entire knowledge graph")
        try:
            entities = await self.entity_service.get_all()
            logger.debug(f"Read {len(entities)} entities from graph")
            return entities
        except Exception:
            logger.exception("Failed to read graph")
            raise

    async def search_nodes(self, query: str) -> Sequence[Entity]:
        """Search for nodes in the knowledge graph."""
        logger.debug(f"Searching nodes with query: {query}")
        try:
            results = await self.entity_service.search(query)
            logger.debug(f"Found {len(results)} matches for '{query}'")
            return results
        except Exception:
            logger.exception(f"Failed to search nodes with query: {query}")
            raise

    async def open_nodes(self, names: List[str]) -> List[EntityIn]:
        """Get specific nodes and their relationships."""
        logger.debug(f"Opening nodes: {names}")

        async def read_node(name: str) -> Optional[EntityIn]:
            try:
                # Get ID from name first
                logger.debug(f"Looking up entity: {name}")
                db_entity = await self.entity_service.get_entity(name)
                if db_entity:
                    logger.debug(f"Found entity in DB: {db_entity.id}")
                    entity = await read_entity_file(self.entities_path, db_entity.id)
                    logger.debug(f"Read entity from filesystem: {entity.id}")
                    return entity
                logger.debug(f"Entity not found: {name}")
                return None
            except Exception:
                logger.exception(f"Failed to read node: {name}")
                return None

        try:
            entities = [entity for entity in await asyncio.gather(*(read_node(name) for name in names))
                       if entity is not None]
            logger.debug(f"Opened {len(entities)} entities")
            return entities
        except Exception:
            logger.exception("Failed to open nodes")
            raise

