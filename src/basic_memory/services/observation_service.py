"""Service for managing observations in the database."""

from typing import List, Sequence

from loguru import logger

from basic_memory.models import Observation as ObservationModel
from basic_memory.models import Entity as EntityModel
from basic_memory.repository.observation_repository import ObservationRepository
from . import FileService
from .exceptions import EntityNotFoundError
from .service import BaseService
from ..repository import EntityRepository
from ..schemas.base import ObservationCategory
from ..schemas.request import ObservationCreate


class ObservationService(BaseService[ObservationRepository]):
    """
    Service for managing observations in the database.
    File operations are handled by MemoryService.
    """

    def __init__(
        self,
        observation_repository: ObservationRepository,
        entity_repository: EntityRepository,
        file_service: FileService,
    ):
        super().__init__(observation_repository)
        self.entity_repository = entity_repository
        self.file_service = file_service

    async def add_observations(
        self, permalink: str, observations: List[ObservationCreate], context: str | None = None
    ) -> EntityModel:
        """Add observations to entity and update its file.

        Observations are added with their categories and written to both
        the database and markdown file. The file format is:
        - [category] Content text #tag1 #tag2 (optional context)

        Args:
            permalink: Entity path ID
            observations: List of observations with categories
            context: Optional shared context for all observations
        """
        logger.debug(f"Adding observations to entity: {permalink}")

        try:
            # Get entity to update
            entity = await self.entity_repository.get_by_permalink(permalink)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {permalink}")

            # Add observations to DB
            await self.repository.create_all(
                [
                    # unpack the ObservationCreate values if present
                    dict(
                        entity_id=entity.id,
                        content=getattr(observation, "content", observation),
                        context=context,
                        category=getattr(observation, "category", None),
                    )
                    for observation in observations
                ]
            )

            # Get updated entity
            entity = await self.entity_repository.get_by_permalink(permalink)

            # Write updated file and checksum
            _, checksum = await self.file_service.write_entity_file(entity)
            await self.entity_repository.update(entity.id, {"checksum": checksum})

            # Return final entity with all updates and relations
            return await self.entity_repository.get_by_permalink(permalink)

        except Exception as e:
            logger.error(f"Failed to add observations: {e}")
            raise

    async def delete_observations(self, permalink: str, observations: List[str]) -> EntityModel:
        """Delete observations from entity and update its file.

        Args:
            permalink: Entity path ID
            observations: List of observation contents to delete
        """
        logger.debug(f"Deleting observations from entity {permalink}")

        try:
            # Get entity
            entity = await self.entity_repository.get_by_permalink(permalink)
            if not entity:
                raise EntityNotFoundError(f"Entity not found: {permalink}")

            # Delete observations from DB by comparing the string value to the Observation content
            for observation in observations:
                result = await self.repository.delete_by_fields(
                    entity_id=entity.id, content=observation
                )

            # Write updated file
            
            # Get fresh entity
            entity = await self.entity_repository.get_by_permalink(permalink)
            _, checksum = await self.file_service.write_entity_file(entity)
            await self.entity_repository.update(entity.id, {"checksum": checksum})

            # Return final entity with all updates
            return await self.entity_repository.get_by_permalink(permalink)

        except Exception as e:
            logger.error(f"Failed to delete observations: {e}")
            raise

    async def delete_by_entity(self, entity_id: int) -> bool:
        """Delete all observations for an entity."""
        logger.debug(f"Deleting all observations for entity: {entity_id}")
        return await self.repository.delete_by_fields(entity_id=entity_id)

    async def get_observations_by_context(self, context: str) -> Sequence[ObservationModel]:
        """Get all observations with a specific context."""
        logger.debug(f"Getting observations for context: {context}")
        return await self.repository.find_by_context(context)

    async def get_observations_by_category(
        self, category: ObservationCategory
    ) -> Sequence[ObservationModel]:
        """Get all observations with a specific context."""
        logger.debug(f"Getting observations for context: {category}")
        return await self.repository.find_by_category(category)

    async def observation_categories(self) -> Sequence[str]:
        """Get all observation categories."""
        logger.debug("Getting observations categories")
        return await self.repository.observation_categories()
