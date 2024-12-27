"""Delete operation schemas for the knowledge graph.

This module defines the request schemas for removing entities, relations,
and observations from the knowledge graph. Each operation has specific
implications and safety considerations.

Deletion Hierarchy:
1. Entity deletion removes the entity and all its relations
2. Relation deletion only removes the connection between entities
3. Observation deletion preserves entity and relations

Key Considerations:
- All deletions are permanent
- Entity deletions cascade to relations
- Files are removed along with entities
- Operations are atomic - they fully succeed or fail
"""

from typing import List, Annotated

from annotated_types import MinLen
from pydantic import BaseModel

from basic_memory.schemas.base import Relation, Observation, PathId


class DeleteEntitiesRequest(BaseModel):
    """Delete one or more entities from the knowledge graph.

    This operation:
    1. Removes the entity from the database
    2. Deletes all observations attached to the entity
    3. Removes all relations where the entity is source or target
    4. Deletes the corresponding markdown file
    """

    path_ids: Annotated[List[PathId], MinLen(1)]


class DeleteRelationsRequest(BaseModel):
    """Delete specific relations between entities.

    This operation removes connections between entities without
    affecting the entities themselves. You must specify the exact
    relation to delete - matching from_id, to_id, and relation_type.
    """

    relations: List[Relation]


class DeleteObservationsRequest(BaseModel):
    """Delete specific observations from an entity.

    This precision operation removes individual observations while
    preserving the entity and all its relations. Observations must
    match exactly for deletion.
    """

    path_id: PathId
    observations: Annotated[List[Observation], MinLen(1)]
