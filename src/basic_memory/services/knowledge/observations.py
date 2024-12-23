"""Observation operations for knowledge service."""

from typing import List

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.observation_service import ObservationService
from .relations import RelationOperations


class ObservationOperations(RelationOperations):
    """Observation operations mixin for KnowledgeService."""

    def __init__(self, *args, observation_service: ObservationService, **kwargs):
        super().__init__(*args, **kwargs)
        self.observation_service = observation_service

    async def add_observations(
        self, entity_id: int, observations: List[str], context: str | None = None
    ) -> EntityModel:
        """Add observations to entity and update its file."""
        logger.debug(f"Adding observations to entity {entity_id}")

        try:
            # Get entity to update
            entity = await self.entity_service.get_entity(entity_id)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {entity_id}")

            # Add observations to DB
            await self.observation_service.add_observations(entity_id, observations, context)

            # Get updated entity
            updated_entity = await self.entity_service.get_entity(entity_id)

            # Write updated file and checksum
            checksum = await self.write_entity_file(entity)
            await self.entity_service.update_entity(entity_id, {"checksum": checksum})

            return updated_entity

        except Exception as e:
            logger.error(f"Failed to add observations: {e}")
            raise

    async def delete_observations(self, entity_id: int, observations: List[str]) -> EntityModel:
        """Delete observations from entity and update its file."""
        logger.debug(f"Deleting observations from entity {entity_id}")

        try:
            # Get updated entity
            entity = await self.entity_service.get_entity(entity_id)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {entity_id}")

            # Delete observations from DB
            await self.observation_service.delete_observations(entity_id, observations)

            # Write updated file
            checksum = await self.write_entity_file(entity)
            await self.entity_service.update_entity(entity_id, {"checksum": checksum})

            # Get final entity with all updates
            return await self.entity_service.get_entity(entity_id)

        except Exception as e:
            logger.error(f"Failed to delete observations: {e}")
            raise
