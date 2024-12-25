"""Service for managing observations in the database."""

from typing import List, Sequence

from loguru import logger
from sqlalchemy import select

from basic_memory.models import Observation as ObservationModel
from basic_memory.repository.observation_repository import ObservationRepository
from .service import BaseService


class ObservationService(BaseService[ObservationRepository]):
    """
    Service for managing observations in the database.
    File operations are handled by MemoryService.
    """

    def __init__(self, observation_repository: ObservationRepository):
        super().__init__(observation_repository)

    async def add_observations(
        self, entity_id: int, observations: List[str], context: str | None = None
    ) -> Sequence[ObservationModel]:
        """Add multiple observations to an entity."""
        logger.debug(f"Adding {len(observations)} observations to entity: {entity_id}")
        return await self.repository.create_all(
            [
                dict(entity_id=entity_id, content=observation, context=context)
                for observation in observations
            ]
        )

    async def delete_observations(self, entity_id: int, contents: List[str]) -> bool:
        """Delete specific observations from an entity."""
        logger.debug(f"Deleting observations from entity: {entity_id}")
        deleted = False
        for content in contents:
            result = await self.repository.delete_by_fields(entity_id=entity_id, content=content)
            if result:
                deleted = True
        return deleted

    async def delete_by_entity(self, entity_id: str) -> bool:
        """Delete all observations for an entity."""
        logger.debug(f"Deleting all observations for entity: {entity_id}")
        return await self.repository.delete_by_fields(entity_id=entity_id)

    async def search_observations(self, query: str) -> List[ObservationModel]:
        """Search for observations across all entities."""
        logger.debug(f"Searching observations with query: {query}")
        result = await self.repository.execute_query(
            select(ObservationModel).filter(
                ObservationModel.content.contains(query) | ObservationModel.context.contains(query)
            )
        )
        observations = result.scalars().all()
        return [ObservationModel(content=obs.content) for obs in observations]

    async def get_observations_by_context(self, context: str) -> Sequence[ObservationModel]:
        """Get all observations with a specific context."""
        logger.debug(f"Getting observations for context: {context}")
        return await self.repository.find_by_context(context)
