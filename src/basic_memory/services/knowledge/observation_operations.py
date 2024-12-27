"""Observation operations for knowledge service."""

from typing import List

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.observation_service import ObservationService
from basic_memory.services.entity_service import EntityService
from basic_memory.schemas.request import ObservationCreate
from .file_operations import FileOperations


class ObservationOperations:
    """Observation operations for knowledge service."""

    def __init__(
        self,
        observation_service: ObservationService,
        entity_service: EntityService,
        file_operations: FileOperations
    ):
        self.observation_service = observation_service
        self.entity_service = entity_service
        self.file_operations = file_operations

    async def add_observations(
        self, 
        path_id: str, 
        observations: List[ObservationCreate], 
        context: str | None = None
    ) -> EntityModel:
        """Add observations to entity and update its file.
        
        Observations are added with their categories and written to both
        the database and markdown file. The file format is:
        - [category] Content text #tag1 #tag2 (optional context)
        
        Args:
            path_id: Entity path ID
            observations: List of observations with categories
            context: Optional shared context for all observations
        """
        logger.debug(f"Adding observations to entity {path_id}")

        try:
            # Get entity to update
            entity = await self.entity_service.get_by_path_id(path_id)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {path_id}")

            # Add observations to DB
            await self.observation_service.add_observations(entity.id, observations, context)

            # Get updated entity
            entity = await self.entity_service.get_by_path_id(path_id)

            # Write updated file and checksum
            _, checksum = await self.file_operations.write_entity_file(entity)
            await self.entity_service.update_entity(path_id, {"checksum": checksum})

            # Return final entity with all updates and relations
            return await self.entity_service.get_by_path_id(path_id)

        except Exception as e:
            logger.error(f"Failed to add observations: {e}")
            raise

    async def delete_observations(
        self,
        path_id: str, 
        observations: List[str]
    ) -> EntityModel:
        """Delete observations from entity and update its file.
        
        Args:
            path_id: Entity path ID
            observations: List of observation contents to delete
        """
        logger.debug(f"Deleting observations from entity {path_id}")

        try:
            # Get entity
            entity = await self.entity_service.get_by_path_id(path_id)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {path_id}")

            # Delete observations from DB
            await self.observation_service.delete_observations(entity.id, observations)

            # Write updated file
            _, checksum = await self.file_operations.write_entity_file(entity)
            await self.entity_service.update_entity(path_id, {"checksum": checksum})

            # Return final entity with all updates
            return await self.entity_service.get_by_path_id(path_id)

        except Exception as e:
            logger.error(f"Failed to delete observations: {e}")
            raise