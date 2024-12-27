"""Relation operations for knowledge service."""

from typing import Sequence, List

from loguru import logger

from basic_memory.models import Entity as EntityModel
from basic_memory.models import Relation as RelationModel
from basic_memory.schemas import Relation as RelationSchema
from basic_memory.services.exceptions import EntityNotFoundError
from basic_memory.services.relation_service import RelationService
from basic_memory.services.entity_service import EntityService
from .entity_operations import EntityOperations
from .file_operations import FileOperations


class RelationOperations:
    """Relation operations for knowledge service."""

    def __init__(
        self,
        relation_service: RelationService,
        entity_service: EntityService,
        file_operations: FileOperations
    ):
        self.relation_service = relation_service
        self.entity_service = entity_service
        self.file_operations = file_operations

    async def create_relations(self, relations: List[RelationSchema]) -> Sequence[EntityModel]:
        """Create relations and return updated entities."""
        logger.debug(f"Creating {len(relations)} relations")
        updated_entities = []
        entities_to_update = set()

        for rs in relations:
            try:
                from_entity = await self.entity_service.get_by_path_id(rs.from_id)
                to_entity = await self.entity_service.get_by_path_id(rs.to_id)

                relation = RelationModel(
                    from_id=from_entity.id,
                    to_id=to_entity.id,
                    relation_type=rs.relation_type,
                    context=rs.context,
                )
                # Create rs in DB
                await self.relation_service.create_relation(relation)

                # Keep track of entities we need to update
                entities_to_update.add(rs.from_id)
                entities_to_update.add(rs.to_id)

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
                continue

        # Get fresh copies of all updated entities
        for path_id in entities_to_update:
            try:
                # Get fresh entity
                entity = await self.entity_service.get_by_path_id(path_id)

                # Write updated file
                _, checksum = await self.file_operations.write_entity_file(entity)
                updated = await self.entity_service.update_entity(path_id, {"checksum": checksum})

                updated_entities.append(updated)

            except Exception as e:
                logger.error(f"Failed to update entity {path_id}: {e}")
                continue
                
        # select again to eagerly load all relations
        return await self.entity_service.open_nodes([e.path_id for e in updated_entities])

    async def delete_relations(self, to_delete: List[RelationSchema]) -> Sequence[EntityModel]:
        """Delete relations and return all updated entities."""
        logger.debug(f"Deleting {len(to_delete)} relations")
        updated_entities = []
        entities_to_update = set()
        relations = []
        
        try:
            # Delete relations from DB
            for relation in to_delete:
                entities_to_update.add(relation.from_id)
                entities_to_update.add(relation.to_id)
                
                relation = await self.relation_service.find_relation(relation.from_id, relation.to_id, relation.relation_type)
                if relation:
                    relations.append(relation)

            # pass Relation models to delete
            num_deleted = await self.relation_service.delete_relations(relations)
            if num_deleted == 0:
                logger.warning("No relations were deleted")

            # Get fresh copies of all updated entities
            for path_id in entities_to_update:
                try:
                    # Get fresh entity
                    entity = await self.entity_service.get_by_path_id(path_id)
                    if not entity:
                        raise EntityNotFoundError(f"Entity not found: {path_id}")

                    # Write updated file
                    _, checksum = await self.file_operations.write_entity_file(entity)
                    updated = await self.entity_service.update_entity(
                        path_id, {"checksum": checksum}
                    )

                    updated_entities.append(updated)

                except Exception as e:
                    logger.error(f"Failed to update entity {path_id}: {e}")
                    continue

            return updated_entities

        except Exception as e:
            logger.error(f"Failed to delete relations: {e}")
            raise