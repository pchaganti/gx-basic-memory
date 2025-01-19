"""Schemas for memory context."""

from datetime import datetime
from typing import Dict, List, Any

from pydantic import AnyUrl, Field, BaseModel

from basic_memory.config import config

"""Memory URL schema for knowledge addressing.

The memory:// URL scheme provides a unified way to address knowledge:

Examples:
    memory://specs/search/*         # Pattern matching 
    memory://specs/xyz              # direct reference
"""


class MemoryUrl(AnyUrl):
    """memory:// URL scheme for knowledge addressing."""

    allowed_schemes = {"memory"}

    # Query params
    params: Dict[str, Any] = Field(default_factory=dict)  # For special modes like 'related'

    @classmethod
    def validate(cls, url: str) -> "MemoryUrl":
        """Validate and construct a MemoryUrl."""

        memory_url = cls(url)

        # if the url host value is not the project name, assume the default project
        if memory_url.host != config.project:
            memory_url = cls(f"memory://{config.project}/{memory_url.host}{memory_url.path}")

        return memory_url

    def relative_path(self) -> str:
        """Get the path without leading slash."""
        path = self.path
        return path[1:] if path.startswith("/") else path

    def __str__(self) -> str:
        """Convert back to URL string."""
        return f"memory://{self.host}{self.path}"


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

    uri: str
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
