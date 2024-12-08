"""Repository for managing Observation objects."""
from typing import Sequence
from sqlalchemy import select

from basic_memory.models import Observation
from basic_memory.repository import Repository


class ObservationRepository(Repository[Observation]):
    """Repository for Observation model with memory-specific operations."""
    
    def __init__(self, session):
        super().__init__(session, Observation)
    
    async def find_by_entity(self, entity_id: str) -> Sequence[Observation]:
        """Find all observations for a specific entity."""
        query = select(Observation).filter(Observation.entity_id == entity_id)
        result = await self.execute_query(query)
        return result.scalars().all()
    
    async def find_by_context(self, context: str) -> Sequence[Observation]:
        """Find observations with a specific context."""
        query = select(Observation).filter(Observation.context == context)
        result = await self.execute_query(query)
        return result.scalars().all()