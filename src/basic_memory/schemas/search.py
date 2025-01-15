"""Search schemas for Basic Memory."""

from typing import Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator


class SearchItemType(str, Enum):
    """Types of searchable items."""
    ENTITY = "entity"
    OBSERVATION = "observation"
    RELATION = "relation"


class SearchQuery(BaseModel):
    """Search query parameters."""
    text: Optional[str] = None  # Made optional to allow permalink-only search
    permalink_pattern: Optional[str] = None  # Added for pattern matching
    types: Optional[List[SearchItemType]] = None
    entity_types: Optional[List[str]] = None
    after_date: Optional[Union[datetime, str]] = None

    @field_validator("after_date")
    @classmethod
    def validate_date(cls, v: Optional[Union[datetime, str]]) -> Optional[str]:
        """Convert datetime to ISO format if needed."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return v  # Assume it's already a string


class SearchResult(BaseModel):
    """Search result item."""
    id: int 
    type: SearchItemType
    score: float
    metadata: dict

    # File-based fields (optional since observations/relations 
    # don't have their own files)
    permalink: Optional[str] = None
    file_path: Optional[str] = None
    
    # Observation-specific fields
    entity_id: Optional[int] = None
    category: Optional[str] = None
    
    # Relation-specific fields
    from_id: Optional[int] = None
    to_id: Optional[int] = None
    relation_type: Optional[str] = None


class SearchResponse(BaseModel):
    """Wrapper for search results list."""
    results: List[SearchResult]