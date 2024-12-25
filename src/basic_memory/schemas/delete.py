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

    Example Request:
    {
        "entity_ids": [
            "component/deprecated_service",
            "document/outdated_spec"
        ]
    }

    Safety Considerations:
    1. Operation is permanent and cannot be undone
    2. All relations involving the entity are lost
    3. File deletion cannot be reversed
    4. Consider creating relations to replacement entities first
    5. Back up important entities before deletion

    Best Practices:
    1. Verify entity IDs carefully before deletion
    2. Document the reason for deletion in related entities
    3. Update dependent entities to reflect the change
    4. Consider marking as deprecated instead of deleting
    5. Create relations to replacement entities if applicable
    """

    entity_ids: Annotated[List[PathId], MinLen(1)]


class DeleteRelationsRequest(BaseModel):
    """Delete specific relations between entities.

    This operation removes connections between entities without
    affecting the entities themselves. You must specify the exact
    relation to delete - matching from_id, to_id, and relation_type.

    Example Request:
    {
        "relations": [
            {
                "from_id": "component/service_a",
                "to_id": "component/old_dep",
                "relation_type": "depends_on",
                "context": "Removing outdated dependency"
            }
        ]
    }

    Safety Considerations:
    1. Operation is permanent
    2. Only affects specified relations
    3. Entities remain unchanged
    4. Relations must match exactly for deletion

    Best Practices:
    1. Delete outdated or incorrect relations promptly
    2. Create replacement relations before deleting if needed
    3. Consider the impact on graph navigation
    4. Document significant relation changes
    5. Verify relation details carefully
    """

    relations: List[Relation]


class DeleteObservationsRequest(BaseModel):
    """Delete specific observations from an entity.

    This precision operation removes individual observations while
    preserving the entity and all its relations. Observations must
    match exactly for deletion.

    Example Request:
    {
        "entity_id": "component/memory_service",
        "deletions": [
            "Old implementation uses Python 3.8",
            "Depends on deprecated module"
        ]
    }

    Safety Considerations:
    1. Operation is permanent
    2. Must match observation text exactly
    3. Entity and relations are preserved
    4. Observation IDs are not reused

    Best Practices:
    1. Consider updating observations instead of deleting
    2. Keep deletion lists focused and specific
    3. Verify observation text carefully
    4. Document replacements for deleted information
    5. Maintain entity's semantic completeness

    Common Use Cases:
    1. Removing outdated information
    2. Correcting incorrect observations
    3. Cleaning up duplicate data
    4. Removing sensitive information
    5. Updating implementation details
    """

    entity_id: PathId
    deletions: Annotated[List[Observation], MinLen(1)]
