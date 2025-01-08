"""Types and utilities for file sync."""

from dataclasses import dataclass, field
from typing import Set, Dict, Optional


@dataclass
class SyncReport:
    """Report of file changes found compared to database state.
    
    Attributes:
        new: Files that exist on disk but not in database
        modified: Files that exist in both but have different checksums
        deleted: Files that exist in database but not on disk
        checksums: Current checksums for files on disk
    """
    new: Set[str] = field(default_factory=set)
    modified: Set[str] = field(default_factory=set)
    deleted: Set[str] = field(default_factory=set)
    checksums: Dict[str, str] = field(default_factory=dict)

    @property
    def total_changes(self) -> int:
        """Total number of files that need attention."""
        return len(self.new) + len(self.modified) + len(self.deleted)
