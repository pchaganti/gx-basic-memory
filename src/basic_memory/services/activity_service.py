"""Service for tracking and querying activity across the knowledge base."""

from datetime import datetime, timezone
from typing import List, Optional

from . import EntityService, RelationService
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
        relation_service: RelationService,
    ):
        """Initialize with required services."""
        self.entity_service = entity_service
        self.relation_service = relation_service

    async def get_recent_activity(
        self,
        timeframe: str = "1d",
        activity_types: Optional[List[str]] = None,
    ) -> RecentActivity:
        """Get all recent activity in the knowledge base.

        Args:
            timeframe: Time window to look back (1h, 1d, 1w, 1m)
            activity_types: Optional list of types to include

        Returns:
            RecentActivity object containing changes and summary
        """
        # Parse timeframe and get cutoff date
        tf = TimeFrame(timeframe)
        since = datetime.now(timezone.utc) - tf.to_timedelta

        # Get changes based on requested types
        changes = []
        types_to_fetch = (
            [ActivityType(t) for t in activity_types] if activity_types else list(ActivityType)
        )

        for activity_type in types_to_fetch:
            if activity_type == ActivityType.ENTITY:
                changes.extend(await self._get_entity_changes(since))
            elif activity_type == ActivityType.RELATION:
                changes.extend(await self._get_relation_changes(since))

        # Sort all changes by timestamp, ensuring timezone awareness
        for change in changes:
            if change.timestamp.tzinfo is None:
                change.timestamp = change.timestamp.replace(tzinfo=timezone.utc)
        changes.sort(key=lambda x: x.timestamp, reverse=True)

        # Generate summary
        summary = ActivitySummary(
            entity_changes=len([c for c in changes if c.activity_type == ActivityType.ENTITY]),
            relation_changes=len([c for c in changes if c.activity_type == ActivityType.RELATION]),
            most_active_paths=self._get_most_active_paths(changes),
        )

        return RecentActivity(timeframe=timeframe, changes=changes, summary=summary)

    async def _get_entity_changes(self, since: datetime) -> List[ActivityChange]:
        """Get recent entity changes."""
        # Query entities updated since the cutoff
        entities = await self.entity_service.get_modified_since(since)

        changes = []
        for entity in entities:
            # Ensure timestamps are timezone-aware
            created_at = (
                entity.created_at.replace(tzinfo=timezone.utc)
                if entity.created_at.tzinfo is None
                else entity.created_at
            )
            updated_at = (
                entity.updated_at.replace(tzinfo=timezone.utc)
                if entity.updated_at.tzinfo is None
                else entity.updated_at
            )

            change_type = ChangeType.CREATED if created_at >= since else ChangeType.UPDATED

            changes.append(
                ActivityChange(
                    activity_type=ActivityType.ENTITY,
                    change_type=change_type,
                    timestamp=updated_at,
                    permalink=entity.permalink,
                    summary=f"{change_type.value.title()} entity: {entity.title}",
                    content=entity.summary,
                )
            )

        return changes

    async def _get_relation_changes(self, since: datetime) -> List[ActivityChange]:
        """Get recent relation changes."""
        # Query relations updated since the cutoff
        relations = await self.relation_service.get_modified_since(since)

        changes = []
        for relation in relations:
            # Ensure timestamps are timezone-aware
            created_at = (
                relation.created_at.replace(tzinfo=timezone.utc)
                if relation.created_at.tzinfo is None
                else relation.created_at
            )
            updated_at = (
                relation.updated_at.replace(tzinfo=timezone.utc)
                if relation.updated_at.tzinfo is None
                else relation.updated_at
            )

            change_type = ChangeType.CREATED if created_at >= since else ChangeType.UPDATED

            changes.append(
                ActivityChange(
                    activity_type=ActivityType.RELATION,
                    change_type=change_type,
                    timestamp=updated_at,
                    permalink=f"{relation.from_id}->{relation.to_id}",
                    summary=(
                        f"{change_type.value.title()} relation: "
                        f"{relation.from_id} {relation.relation_type} {relation.to_id}"
                    ),
                    content=relation.context,
                )
            )

        return changes

    def _get_most_active_paths(self, changes: List[ActivityChange], limit: int = 5) -> List[str]:
        """Get the most frequently changed paths."""
        path_counts = {}
        for change in changes:
            path_counts[change.permalink] = path_counts.get(change.permalink, 0) + 1

        # Sort by count descending and take top paths
        sorted_paths = sorted(
            path_counts.items(),
            key=lambda x: (-x[1], x[0]),  # Sort by count desc, then path asc
        )

        return [path for path, _ in sorted_paths[:limit]]
