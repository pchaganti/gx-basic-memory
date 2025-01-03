"""Service for managing entities in the database."""

from typing import Dict, Any, Sequence, List, Optional

from loguru import logger

from basic_memory.models import Entity as EntityModel, Observation
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.schemas import Entity as EntitySchema
from basic_memory.services.exceptions import EntityNotFoundError
from .service import BaseService


def entity_model(entity: EntitySchema):
    model = EntityModel(
        name=entity.name,
        entity_type=entity.entity_type,
        path_id=entity.path_id,
        file_path=entity.path_id,
        description=entity.description,
        observations=[Observation(content=observation) for observation in entity.observations],
    )
    return model


class EntityService(BaseService[EntityModel]):
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

    async def update_entity(self, path_id: str, update_data: Dict[str, Any]) -> EntityModel:
        """Update an entity's fields."""
        logger.debug(f"Updating entity path_id: {path_id} with data: {update_data}")
        entity = await self.get_by_path_id(path_id)

        updated = await self.repository.update(entity.id, update_data)
        if not updated:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        return updated

    async def get_by_path_id(self, path_id: str) -> EntityModel:
        """Get entity by type and name combination."""
        logger.debug(f"Getting entity by path_id: {path_id}")
        db_entity = await self.repository.get_by_path_id(path_id)
        if not db_entity:
            raise EntityNotFoundError(f"Entity not found: {path_id}")
        return db_entity

    async def get_all(self) -> Sequence[EntityModel]:
        """Get all entities."""
        return await self.repository.find_all()
        
    async def get_entity_types(self) -> List[str]:
        """Get list of all distinct entity types in the system."""
        logger.debug("Getting all distinct entity types")
        return await self.repository.get_entity_types()
        
    async def list_entities(
        self, 
        entity_type: Optional[str] = None,
        sort_by: Optional[str] = "updated_at",
        include_related: bool = False,
    ) -> Sequence[EntityModel]:
        """List entities with optional filtering and sorting."""
        logger.debug(f"Listing entities: type={entity_type} sort={sort_by}")
        return await self.repository.list_entities(
            entity_type=entity_type,
            sort_by=sort_by
        )

    async def delete_entity(self, path_id: str) -> bool:
        """Delete entity from database."""
        logger.debug(f"Deleting entity path_id: {path_id}")
        entity = await self.get_by_path_id(path_id)
        return await self.repository.delete(entity.id)

    async def open_nodes(self, path_ids: List[str]) -> Sequence[EntityModel]:
        """Get specific nodes and their relationships."""
        logger.debug(f"Opening nodes path_ids: {path_ids}")
        return await self.repository.find_by_path_ids(path_ids)

    async def delete_entities(self, path_ids: List[str]) -> bool:
        """Delete entities and their files."""
        logger.debug(f"Deleting entities: {path_ids}")
        deleted_count = await self.repository.delete_by_path_ids(path_ids)
        return deleted_count > 0

    async def delete_entity_by_file_path(self, file_path):
        await self.repository.delete_by_file_path(file_path)