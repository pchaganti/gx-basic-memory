from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TimeFrame:
    """Represents a time period for querying activity."""
    
    def __init__(self, timeframe_str: str):
        """Parse timeframe string (e.g., '1d', '2w', '1m')"""
        if not timeframe_str or len(timeframe_str) < 2:
            raise ValueError("Invalid timeframe format")
            
        try:
            self.value = int(timeframe_str[:-1])
            self.unit = timeframe_str[-1]
        except ValueError:
            raise ValueError("Invalid timeframe format")
            
        if self.unit not in ['h', 'd', 'w', 'm']:
            raise ValueError("Invalid timeframe unit")
            
        if self.value < 1:
            raise ValueError("Timeframe value must be positive")
            
    @property
    def to_timedelta(self) -> timedelta:
        """Convert to Python timedelta."""
        if self.unit == 'h':
            return timedelta(hours=self.value)
        elif self.unit == 'd':
            return timedelta(days=self.value)
        elif self.unit == 'w':
            return timedelta(weeks=self.value)
        elif self.unit == 'm':
            # Approximate month as 30 days
            return timedelta(days=self.value * 30)
        else:
            raise ValueError(f"Invalid unit: {self.unit}")


class ActivityType(str, Enum):
    """Types of activities that can be tracked."""
    ENTITY = "entity"
    RELATION = "relation"


class ChangeType(str, Enum):
    """Types of changes that can occur."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class ActivityChange(BaseModel):
    """Represents a single change in the system."""
    activity_type: ActivityType
    change_type: ChangeType
    timestamp: datetime
    path_id: str
    summary: str
    content: Optional[str] = None


class ActivitySummary(BaseModel):
    """Summary statistics about recent activity."""
    entity_changes: int = Field(default=0, description="Number of entity changes")
    relation_changes: int = Field(default=0, description="Number of relation changes")
    most_active_paths: List[str] = Field(
        default_factory=list,
        description="List of most frequently changed paths"
    )


class RecentActivity(BaseModel):
    """Complete activity report."""
    timeframe: str
    changes: List[ActivityChange] = Field(default_factory=list)
    summary: ActivitySummary
