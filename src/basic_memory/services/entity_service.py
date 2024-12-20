"""Service for managing entities in the database."""

from typing import Dict, Any, Sequence, List

from loguru import logger

from basic_memory.fileio import EntityNotFoundError
from basic_memory.models import Entity as EntityModel, Observation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import Entity as EntitySchema
from .service import BaseService


def entity_model(entity):
    model = EntityModel(
        id=EntityModel.generate_id(entity.entity_type, entity.name),
        name=entity.name,
        entity_type=entity.entity_type,
        description=entity.description,
        observations=[Observation(content=observation) for observation in entity.observations],
    )
    return model


class EntityService(BaseService[EntityRepository]):
    """Service for managing entities in the database."""

    def __init__(self, entity_repository: EntityRepository):
        super().__init__(entity_repository)

    async def search(self, query: str) -> Sequence[EntityModel]:
        """Search entities using LIKE pattern matching."""
        logger.debug(f"Searching entities with query: {query}")
        return await self.repository.search(query)

    async def create_entity(self, entity: EntitySchema) -> EntityModel:
        """Create a new entity in the database."""
        logger.debug(f"Creating entity in DB: {entity}")
        model = entity_model(entity)
        return await self.repository.add(model)

    async def create_entities(self, entities_in: List[EntitySchema]) -> Sequence[EntityModel]:
        """Create multiple entities with their observations."""
        logger.debug(f"Creating {len(entities_in)} entities")
        created = await self.repository.add_all([entity_model(entity) for entity in entities_in])
        return created

    async def update_entity(self, entity_id: str, update_data: Dict[str, Any]) -> EntityModel:
        """Update an entity's fields."""
        logger.debug(f"Updating entity {entity_id} with data: {update_data}")
        updated = await self.repository.update(entity_id, update_data)
        if not updated:
            raise EntityNotFoundError(f"Entity not found: {entity_id}")
        return updated

    async def get_entity(self, entity_id: str) -> EntityModel:
        """Get entity by ID."""
        logger.debug(f"Getting entity by ID: {entity_id}")
        db_entity = await self.repository.find_by_id(entity_id)
        if not db_entity:
            raise EntityNotFoundError(f"Entity not found: {entity_id}")
        return db_entity

    async def get_by_type_and_name(self, entity_type: str, name: str) -> EntityModel:
        """Get entity by type and name combination."""
        logger.debug(f"Getting entity by type/name: {entity_type}/{name}")
        db_entity = await self.repository.find_by_type_and_name(entity_type, name)
        if not db_entity:
            raise EntityNotFoundError(f"Entity not found: {entity_type}/{name}")
        return db_entity

    async def get_all(self) -> Sequence[EntityModel]:
        """Get all entities."""
        return await self.repository.find_all()

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from database."""
        logger.debug(f"Deleting entity: {entity_id}")
        return await self.repository.delete(entity_id)

    async def open_nodes(self, entity_ids: List[str]) -> Sequence[EntityModel]:
        """Get specific nodes and their relationships."""
        logger.debug(f"Opening nodes entity_ids: {entity_ids}")
        return await self.repository.find_by_ids(entity_ids)

    async def delete_entities(self, entity_ids: List[str]) -> bool:
        """Delete entities and their files."""
        logger.debug(f"Deleting entities: {entity_ids}")
        deleted_count = await self.repository.delete_by_ids(entity_ids)
        return deleted_count > 0
