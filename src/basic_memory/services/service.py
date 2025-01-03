"""Base service class."""

from datetime import datetime
from typing import TypeVar, Generic, List, Sequence

from basic_memory.models import Base
from basic_memory.repository.repository import Repository

T = TypeVar("T", bound=Base)
R = TypeVar("R", bound=Repository)

class BaseService(Generic[T]):
    """Base service that takes a repository."""

    def __init__(self, repository: R):
        """Initialize service with repository."""
        self.repository = repository

    async def add(self, model: T) -> T:
        """Add model to repository."""
        return await self.repository.add(model)

    async def add_all(self, models: List[T]) -> Sequence[T]:
        """Add a List of models to repository."""
        return await self.repository.add_all(models)

    async def get_modified_since(self, since: datetime) -> Sequence[T]:
        """Get all items modified since the given timestamp.
        
        Args:
            since: Datetime to search from
            
        Returns:
            Sequence of items modified since the timestamp
        """
        return await self.repository.find_modified_since(since)