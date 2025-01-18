"""Schemas for memory context."""

from typing import Dict, List, Optional, Any
from pydantic import AnyUrl, Field, BaseModel

from basic_memory.schemas.search import SearchResult, RelatedResult
from basic_memory.config import config

"""Memory URL schema for knowledge addressing.

The memory:// URL scheme provides a unified way to address knowledge:

Examples:
    memory://specs/search/*         # Pattern matching 
    memory://specs/xyz              # direct reference
"""


class MemoryUrl(AnyUrl):
    """memory:// URL scheme for knowledge addressing."""
    
    allowed_schemes = {'memory'}

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


class GraphContext(BaseModel):
    """Complete context response."""

    # Direct matches
    primary_entities: List[SearchResult] = Field(description="Entities directly matching URI")

    # Related entities
    related_entities: List[RelatedResult] = Field(description="Entities found via relations")

    # Context metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        example={
            "uri": "memory://specs/search/*",
            "depth": 2,
            "timeframe": "7d",
            "generated_at": "2024-01-14T12:00:00Z",
            "matched_entities": 3,
            "total_entities": 8,
            "total_relations": 12,
        },
    )