"""Search schemas for Basic Memory."""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class SearchItemType(str, Enum):
    """Types of searchable items."""
    DOCUMENT = "document"
    ENTITY = "entity"


class SearchQuery(BaseModel):
    """Search query parameters."""
    text: str
    types: Optional[List[SearchItemType]] = None
    entity_types: Optional[List[str]] = None
    after_date: Optional[datetime] = None


class SearchResult(BaseModel):
    """Search result item."""
    path_id: str
    file_path: str
    type: SearchItemType
    score: float
    metadata: dict