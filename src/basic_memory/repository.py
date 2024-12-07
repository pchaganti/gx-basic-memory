from typing import Type, Optional, Any, Sequence
from sqlalchemy import select, func, Select, Executable, inspect, Result, Column, and_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, selectinload

from basic_memory.models import Entity, Observation, Relation, Base


class Repository[T: Base]:
    """
    Generic repository pattern implementation for handling database operations.
    Adapted for basic-memory with string IDs and memory-specific operations.

    Provides basic CRUD operations with an async session.

    :param session: Async database session from SQLAlchemy.
    :param Model: Database model class.

    Example usage:
        async with async_sessionmaker() as session:
            entity_repo = Repository(session, Entity)
            entity = await entity_repo.create({
                'id': '20240102-some-entity',
                'name': 'Example Entity',
                'entity_type': 'concept'
            })
    """

    def __init__(self, session: AsyncSession, Model: Type[T]):
        self.session = session
        self.Model = Model
        self.primary_key: Column[Any] = inspect(self.Model).mapper.primary_key[0]
        self.valid_columns = [column.key for column in inspect(self.Model).columns]

    async def refresh(self, instance: T) -> None:
        """
        Refresh the state of the given instance from the database.

        :param instance: Instance to refresh
        """
        await self.session.refresh(instance)

    async def find_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        """
        Fetches records from the database with pagination.

        :param skip: Number of records to skip.
        :param limit: Maximum number of records to fetch.
        :return: List containing the fetched records.
        """
        result = await self.session.execute(
            select(self.Model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """
        Fetches an entity by its unique identifier asynchronously.

        :param entity_id: Unique identifier of the entity (string timestamp-based ID)
        :return: The entity if found, otherwise None

        Example:
            entity = await repository.find_by_id('20240102-example-entity')
        """
        try:
            result = await self.session.execute(
                select(self.Model).filter(self.primary_key == entity_id)
            )
            return result.scalars().one()
        except NoResultFound:
            return None

    async def create(self, entity_data: dict) -> T:
        """
        Creates a new entity in the database from the provided data dictionary.

        :param entity_data: A dictionary containing data to be inserted
        :return: The created entity

        Example:
            >>> entity_data = {
            ...     'id': '20240102-example',
            ...     'name': 'Example Entity',
            ...     'entity_type': 'concept',
            ...     'description': 'An example entity'
            ... }
            >>> new_entity = await repo.create(entity_data)
        """
        model_data = {k: v for k, v in entity_data.items() if k in self.valid_columns}
        entity = self.Model(**model_data)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity_id: str, entity_data: dict) -> Optional[T]:
        """
        Updates an entity with given entity_id using the provided entity_data.

        :param entity_id: String ID of the entity to update
        :param entity_data: Dictionary containing the data to update
        :return: The updated entity or None if not found

        Example:
            updated = await repository.update('20240102-example', {'description': 'Updated description'})
        """
        try:
            result = await self.session.execute(
                select(self.Model).filter(self.primary_key == entity_id)
            )
            entity = result.scalars().one()
            for key, value in entity_data.items():
                if key in self.valid_columns:
                    setattr(entity, key, value)
            await self.session.flush()
            return entity
        except NoResultFound:
            return None

    async def delete(self, entity_id: str) -> bool:
        """
        Deletes an entity from the database.

        :param entity_id: String ID of the entity to delete
        :return: Boolean indicating if the entity was deleted

        Example:
            success = await repository.delete('20240102-example')
        """
        try:
            result = await self.session.execute(
                select(self.Model).filter(self.primary_key == entity_id)
            )
            entity = result.scalars().one()
            await self.session.delete(entity)
            await self.session.flush()
            return True
        except NoResultFound:
            return False

    async def count(self, query: Executable | None = None) -> int:
        """
        Counts entities in the database table.

        :param query: Optional SQL query to modify the count operation
        :return: Number of matching entities
        """
        if query is None:
            query = select(func.count()).select_from(self.Model)
        result = await self.session.execute(query)
        scalar = result.scalar()
        return scalar if scalar is not None else 0

    async def execute_query(self, query: Executable) -> Result[Any]:
        """
        Executes the given query asynchronously.

        :param query: An executable query instance
        :return: Query result
        """
        return await self.session.execute(query)

    async def find_one(self, query: Select[tuple[T]]) -> Optional[T]:
        """
        Executes a query and retrieves a single record.

        :param query: The query to execute
        :return: Single record or None
        """
        result = await self.execute_query(query)
        return result.scalars().one_or_none()


class EntityRepository(Repository[Entity]):
    """
    Repository for Entity model with memory-specific operations.
    """
    
    async def find_by_id(self, entity_id: str) -> Optional[Entity]:
        """
        Find entity by ID with relations eagerly loaded.
        
        Uses selectinload to eagerly load outgoing and incoming relations in a single query.
        This is necessary because:
        1. In async code, lazy loading relations after the session closes doesn't work
        2. Our service layer often needs the complete entity with its relations
        3. Using a single query with selectinload is more efficient than multiple lazy-loaded queries
        
        :param entity_id: Entity ID to search for
        :return: Entity if found with all relations loaded, None otherwise
        
        Example:
            entity = await repo.find_by_id('20240102-entity-123')
            # Relations are already loaded - no additional queries needed
            for relation in entity.outgoing_relations:
                print(f"Related to {relation.to_id} via {relation.relation_type}")
        """
        try:
            result = await self.session.execute(
                select(Entity)
                .filter(Entity.id == entity_id)
                .options(
                    selectinload(Entity.outgoing_relations),
                    selectinload(Entity.incoming_relations)
                )
            )
            return result.scalars().one()
        except NoResultFound:
            return None

    async def find_by_name(self, name: str) -> Optional[Entity]:
        """
        Find an entity by its unique name.
        
        :param name: Entity name to search for
        :return: Entity if found, None otherwise
        """
        query = select(Entity).filter(Entity.name == name)
        return await self.find_one(query)
    
    async def search_by_type(self, entity_type: str, skip: int = 0, limit: int = 100) -> Sequence[Entity]:
        """
        Search for entities of a specific type.
        
        :param entity_type: Type to search for
        :param skip: Number of records to skip
        :param limit: Maximum records to return
        :return: List of matching entities
        """
        query = select(Entity).filter(Entity.entity_type == entity_type).offset(skip).limit(limit)
        result = await self.execute_query(query)
        return result.scalars().all()


class ObservationRepository(Repository[Observation]):
    """
    Repository for Observation model with memory-specific operations.
    """
    
    async def find_by_entity(self, entity_id: str) -> Sequence[Observation]:
        """
        Find all observations for a specific entity.
        
        :param entity_id: ID of the entity to find observations for
        :return: List of observations
        """
        query = select(Observation).filter(Observation.entity_id == entity_id)
        result = await self.execute_query(query)
        return result.scalars().all()
    
    async def find_by_context(self, context: str) -> Sequence[Observation]:
        """
        Find observations with a specific context.
        
        :param context: Context to search for
        :return: List of matching observations
        """
        query = select(Observation).filter(Observation.context == context)
        result = await self.execute_query(query)
        return result.scalars().all()


class RelationRepository(Repository[Relation]):
    """
    Repository for Relation model with memory-specific operations.
    """
    
    async def find_by_entities(self, from_id: str, to_id: str) -> Sequence[Relation]:
        """
        Find all relations between two entities.
        
        :param from_id: Source entity ID
        :param to_id: Target entity ID
        :return: List of relations between the entities
        """
        query = select(Relation).filter(
            and_(
                Relation.from_id == from_id,
                Relation.to_id == to_id
            )
        )
        result = await self.execute_query(query)
        return result.scalars().all()
    
    async def find_by_type(self, relation_type: str) -> Sequence[Relation]:
        """
        Find all relations of a specific type.
        
        :param relation_type: Type of relation to find
        :return: List of matching relations
        """
        query = select(Relation).filter(Relation.relation_type == relation_type)
        result = await self.execute_query(query)
        return result.scalars().all()