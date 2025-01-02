from dataclasses import dataclass, field
from typing import Optional, Set, Dict


@dataclass
class FileState:
    """State of a file including path and checksum info."""
    path: str
    checksum: str
    moved_from: Optional[str] = None


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
    moved: Dict[str, FileState] = field(default_factory=dict)  # new_path -> state
    checksums: Dict[str, str] = field(default_factory=dict)  # path -> checksum

    @property
    def total_changes(self) -> int:
        """Total number of files that need attention."""
        return len(self.new) + len(self.modified) + len(self.deleted)
