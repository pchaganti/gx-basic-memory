"""Schemas for memory context."""

from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from pydantic import field_validator

from basic_memory.schemas.search import SearchResult, RelatedResult

"""Memory URL schema for knowledge addressing.

The memory:// URL scheme provides a unified way to address knowledge across projects:
memory://project-name/path/to/content

Examples:
    memory://basic-memory/specs/search/*      # Pattern matching
    memory://basic-memory/specs/xyz           # Exact permalink
    memory://basic-memory/related/sync        # Related content
"""


class MemoryUrl(BaseModel):
    """memory:// URL scheme for knowledge addressing."""

    scheme: str = Field(default="memory", frozen=True)
    host: str  # Project identifier
    path: str  # Full path

    # Query params
    params: Dict[str, Any] = Field(default_factory=dict)  # For special modes like 'related'

    @field_validator("scheme")
    @classmethod
    def validate_scheme(cls, v: str) -> str:
        """Validate URL scheme."""
        if v != "memory":
            raise ValueError("URL must use memory:// scheme")
        return v

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: Optional[str]) -> str:
        """Validate host (project identifier)."""
        if not v:
            raise ValueError("URL must include project/context identifier")
        return v

    @classmethod
    def parse(cls, url_str: str) -> "MemoryUrl":
        """Parse a memory:// URL string."""
        # Split scheme and rest
        if "://" not in url_str:
            raise ValueError("URL must include scheme (memory://)")

        scheme, rest = url_str.split("://", 1)

        # Split host and path
        parts = rest.split("/", 1)
        if len(parts) != 2:
            raise ValueError("URL must include both host and path")

        host, path = parts
        path = "/" + path  # Add leading slash

        # Create base URL
        url = cls(scheme=scheme, host=host, path=path)

        # Parse special patterns
        path_no_slash = path[1:] if path.startswith("/") else path

        # Extract special prefixes
        segments = path_no_slash.split("/")
        if segments and segments[0] in {"related", "context"}:
            url.params["type"] = segments[0]
            url.params["target"] = "/".join(segments[1:])

        return url

    @property
    def project(self) -> str:
        """Get the project/context identifier."""
        return self.host

    def relative_path(self) -> str:
        """Get the path without leading slash."""
        return self.path[1:] if self.path.startswith("/") else self.path

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
