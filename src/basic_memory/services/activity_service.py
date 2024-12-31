from datetime import datetime
from typing import List, Optional, Sequence

from . import EntityService, DocumentService, RelationService
from ..models import Document
from ..schemas.activity import (
    ActivityChange,
    ActivitySummary,
    ActivityType,
    ChangeType,
    RecentActivity,
    TimeFrame,
)


class ActivityService:
    """Service for tracking and querying activity across the knowledge base."""

    def __init__(
        self,
        entity_service: EntityService,
        document_service: DocumentService,
        relation_service: RelationService,
    ):
        """Initialize with required services."""
        self.entity_service = entity_service
        self.document_service = document_service
        self.relation_service = relation_service

    async def get_recent_activity(
        self,
        timeframe: str = "1d",
        activity_types: Optional[List[str]] = None,
        include_content: bool = True
    ) -> RecentActivity:
        """Get all recent activity in the knowledge base.
        
        Args:
            timeframe: Time window to look back (1h, 1d, 1w, 1m)
            activity_types: Optional list of types to include
            include_content: Whether to include full content
            
        Returns:
            RecentActivity object containing changes and summary
        """
        # Parse timeframe and get cutoff date
        tf = TimeFrame(timeframe)
        since = datetime.utcnow() - tf.to_timedelta

        # Get changes based on requested types
        changes = []
        types_to_fetch = (
            [ActivityType(t) for t in activity_types]
            if activity_types
            else list(ActivityType)
        )

        for activity_type in types_to_fetch:
            if activity_type == ActivityType.ENTITY:
                changes.extend(await self._get_entity_changes(since))
            elif activity_type == ActivityType.DOCUMENT:
                changes.extend(await self._get_document_changes(since))
            elif activity_type == ActivityType.RELATION:
                changes.extend(await self._get_relation_changes(since))

        # Sort all changes by timestamp
        changes.sort(key=lambda x: x.timestamp, reverse=True)

        # Remove content if not requested
        if not include_content:
            for change in changes:
                change.content = None

        # Generate summary
        summary = ActivitySummary(
            document_changes=len([c for c in changes if c.activity_type == ActivityType.DOCUMENT]),
            entity_changes=len([c for c in changes if c.activity_type == ActivityType.ENTITY]),
            relation_changes=len([c for c in changes if c.activity_type == ActivityType.RELATION]),
            most_active_paths=self._get_most_active_paths(changes)
        )

        return RecentActivity(
            timeframe=timeframe,
            changes=changes,
            summary=summary
        )

    async def _get_entity_changes(self, since: datetime) -> List[ActivityChange]:
        """Get recent entity changes."""
        # Query entities updated since the cutoff
        entities = await self.entity_service.get_modified_since(since)
        
        changes = []
        for entity in entities:
            change_type = (
                ChangeType.CREATED 
                if entity.created_at >= since 
                else ChangeType.UPDATED
            )
            
            changes.append(
                ActivityChange(
                    activity_type=ActivityType.ENTITY,
                    change_type=change_type,
                    timestamp=entity.updated_at,
                    path_id=entity.path_id,
                    summary=f"{change_type.value.title()} entity: {entity.name}",
                    content=entity.description
                )
            )
            
        return changes

    async def _get_document_changes(self, since: datetime) -> List[ActivityChange]:
        """Get recent document changes."""
        # Query documents updated since the cutoff
        documents: Sequence[Document] = await self.document_service.get_modified_since(since)
        
        changes = []
        for doc in documents:
            change_type = (
                ChangeType.CREATED 
                if doc.created_at >= since 
                else ChangeType.UPDATED
            )
            
            changes.append(
                ActivityChange(
                    activity_type=ActivityType.DOCUMENT,
                    change_type=change_type,
                    timestamp=doc.updated_at,
                    path_id=doc.path_id,
                    summary=f"{change_type.value.title()} document: {doc.path_id}",
                    #content=doc.content[:500] if doc.content else None  # First 500 chars
                )
            )
            
        return changes

    async def _get_relation_changes(self, since: datetime) -> List[ActivityChange]:
        """Get recent relation changes."""
        # Query relations updated since the cutoff
        relations = await self.relation_service.get_modified_since(since)
        
        changes = []
        for relation in relations:
            change_type = (
                ChangeType.CREATED 
                if relation.created_at >= since 
                else ChangeType.UPDATED
            )
            
            changes.append(
                ActivityChange(
                    activity_type=ActivityType.RELATION,
                    change_type=change_type,
                    timestamp=relation.updated_at,
                    path_id=f"{relation.from_id}->{relation.to_id}",
                    summary=(
                        f"{change_type.value.title()} relation: "
                        f"{relation.from_id} {relation.relation_type} {relation.to_id}"
                    ),
                    content=relation.context
                )
            )
            
        return changes

    def _get_most_active_paths(self, changes: List[ActivityChange], limit: int = 5) -> List[str]:
        """Get the most frequently changed paths."""
        path_counts = {}
        for change in changes:
            path_counts[change.path_id] = path_counts.get(change.path_id, 0) + 1
            
        # Sort by count descending and take top paths
        sorted_paths = sorted(
            path_counts.items(),
            key=lambda x: (-x[1], x[0])  # Sort by count desc, then path asc
        )
        
        return [path for path, _ in sorted_paths[:limit]]
