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
    """Report of file changes found."""
    new: Set[str] = field(default_factory=set)
    modified: Set[str] = field(default_factory=set)
    deleted: Set[str] = field(default_factory=set)
    moved: Dict[str, FileState] = field(default_factory=dict)  # new_path -> state
    checksums: Dict[str, str] = field(default_factory=dict)  # path -> checksum

    @property
    def total_changes(self) -> int:
        return len(self.new) + len(self.modified) + len(self.deleted) + len(self.moved)
