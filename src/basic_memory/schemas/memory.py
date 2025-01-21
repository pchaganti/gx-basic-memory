"""Schemas for memory context."""

from datetime import datetime
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, field_validator, Field

from basic_memory.schemas.search import SearchItemType


class MemoryUrl(BaseModel):
    """memory:// URL scheme for knowledge addressing.
    
    Example URLs:
        memory://specs/search         # Direct reference
        memory://specs/search/*      # Pattern matching
        memory://related/xyz         # Special lookup
    """
    url: str
    path: str = ""
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate the URL starts with memory://."""
        if isinstance(v, MemoryUrl):
            return v.url
        if not isinstance(v, str):
            raise ValueError(f"URL must be a string, got {type(v)}")
        if not v.startswith("memory://"):
            raise ValueError(f"Invalid memory URL: {v}. Must start with memory://")
        return v
        
    def __init__(self, url: str, **data):
        if isinstance(url, MemoryUrl):
            url = url.url
        super().__init__(url=url, **data)
        self.path = url.removeprefix("memory://")
        
    @classmethod
    def validate(cls, url: str) -> "MemoryUrl":
        """Validate and construct a MemoryUrl."""
        return cls(url=url)

    def relative_path(self) -> str:
        """Get the path."""
        return self.path

    def __str__(self) -> str:
        """Convert back to URL string."""
        return self.url


class EntitySummary(BaseModel):
    """Simplified entity representation."""

    permalink: str
    title: str
    file_path: str
    created_at: datetime


class RelationSummary(BaseModel):
    """Simplified relation representation."""

    permalink: str
    type: str
    from_id: str
    to_id: str
    created_at: datetime


class ObservationSummary(BaseModel):
    """Simplified observation representation."""

    permalink: str
    category: str
    content: str


class MemoryMetadata(BaseModel):
    """Simplified response metadata."""

    uri: Optional[str] = None
    types: Optional[List[SearchItemType]] = None
    depth: int
    timeframe: str
    generated_at: datetime
    total_results: int
    total_relations: int


class GraphContext(BaseModel):
    """Complete context response."""

    # Direct matches
    primary_results: List[EntitySummary | RelationSummary | ObservationSummary] = Field(
        description="results directly matching URI"
    )

    # Related entities
    related_results: List[EntitySummary | RelationSummary | ObservationSummary] = Field(
        description="related results"
    )

    # Context metadata
    metadata: MemoryMetadata