"""Search schemas for Basic Memory."""

from typing import Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator


class SearchItemType(str, Enum):
    """Types of searchable items."""

    DOCUMENT = "document"
    ENTITY = "entity"


class SearchQuery(BaseModel):
    """Search query parameters."""

    text: str
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

    permalink: str
    file_path: str
    type: SearchItemType
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    """Wrapper for search results list."""

    results: List[SearchResult]
