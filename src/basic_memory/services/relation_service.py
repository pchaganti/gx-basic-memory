"""Service for managing relations in the database."""

from typing import List, Sequence

from loguru import logger

from basic_memory.schemas import Relation as RelationSchema
from basic_memory.models import Entity as EntityModel, Relation as RelationModel
from basic_memory.repository.relation_repository import RelationRepository
from . import FileService
from .exceptions import EntityNotFoundError
from .service import BaseService
from ..repository import EntityRepository


class RelationService(BaseService[RelationRepository]):
    """
    Service for managing relations in the database.
    File operations are handled by MemoryService.
    """

    def __init__(
        self,
        relation_repository: RelationRepository,
        entity_repository: EntityRepository,
        file_service: FileService,
    ):
        super().__init__(relation_repository)
        self.entity_repository = entity_repository
        self.file_service = file_service

    async def create_relations(self, relations: List[RelationSchema]) -> Sequence[EntityModel]:
        """Create relations and return updated entities."""
        logger.debug(f"Creating {len(relations)} relations")
        updated_entities = []
        entities_to_update = set()

        for rs in relations:
            try:
                from_entity = await self.entity_repository.get_by_path_id(rs.from_path_id)
                to_entity = await self.entity_repository.get_by_path_id(rs.to_path_id)

                relation = RelationModel(
                    from_id=from_entity.id,
                    to_id=to_entity.id,
                    relation_type=rs.relation_type,
                    context=rs.context,
                )
                # Create relation in DB
                await self.repository.add(relation)

                # Keep track of entities we need to update
                entities_to_update.add(rs.from_path_id)
                entities_to_update.add(rs.to_path_id)

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
                continue

        # Get fresh copies of all updated entities
        for path_id in entities_to_update:
            try:
                # Get fresh entity
                entity = await self.entity_repository.get_by_path_id(path_id)

                # Write updated file
                _, checksum = await self.file_service.write_entity_file(entity)
                updated = await self.entity_repository.update(entity.id, {"checksum": checksum})

                updated_entities.append(updated)

            except Exception as e:
                logger.error(f"Failed to update entity {path_id}: {e}")
                continue

        # select again to eagerly load all relations
        return await self.entity_repository.find_by_path_ids([e.path_id for e in updated_entities])

    async def delete_relations(self, to_delete: List[RelationSchema]) -> Sequence[EntityModel]:
        """Delete relations and return all updated entities."""
        logger.debug(f"Deleting {len(to_delete)} relations")
        updated_entities = []
        entities_to_update = set()
        relations = []

        try:
            # Delete relations from DB
            for relation in to_delete:
                entities_to_update.add(relation.from_path_id)
                entities_to_update.add(relation.to_path_id)

                relation = await self.find_relation(
                    relation.from_path_id, relation.to_path_id, relation.relation_type
                )
                if relation:
                    relations.append(relation)

            # pass Relation models to delete

            ids = [relation.id for relation in relations]
            num_deleted = await self.repository.delete_by_ids(ids)

            if num_deleted == 0:
                logger.warning("No relations were deleted")

            # Get fresh copies of all updated entities
            for path_id in entities_to_update:
                try:
                    # Get fresh entity
                    entity = await self.entity_repository.get_by_path_id(path_id)
                    if not entity:
                        raise EntityNotFoundError(f"Entity not found: {path_id}")

                    # Write updated file
                    _, checksum = await self.file_service.write_entity_file(entity)
                    updated = await self.entity_repository.update(entity.id, {"checksum": checksum})

                    updated_entities.append(updated)

                except Exception as e:
                    logger.error(f"Failed to update entity {path_id}: {e}")
                    continue

            return updated_entities

        except Exception as e:
            logger.error(f"Failed to delete relations: {e}")
            raise

    async def find_relation(
        self, from_path_id: str, to_path_id: str, relation_type: str
    ) -> RelationModel:
        return await self.repository.find_relation(from_path_id, to_path_id, relation_type)

    async def delete_relation(
        self, from_entity: EntityModel, to_entity: EntityModel, relation_type: str
    ) -> bool:
        """Delete a specific relation between entities."""
        logger.debug(f"Deleting relation between {from_entity.id} and {to_entity.id}")

        assert from_entity.id is not None, "from_entity.id must not be None"
        result = await self.repository.delete_by_fields(
            from_id=from_entity.id,
            to_id=to_entity.id,
            relation_type=relation_type,
        )
        return result

    async def delete_outgoing_relations_from_entity(self, entity_id: int) -> None:
        logger.debug(f"Deleting outgoing relations from {entity_id} ")
        return await self.repository.delete_outgoing_relations_from_entity(entity_id)
