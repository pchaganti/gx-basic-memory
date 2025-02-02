"""Watch service for Basic Memory."""

import json
import dataclasses

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from watchfiles import awatch, Change
import os

from basic_memory.config import ProjectConfig
from basic_memory.sync.sync_service import SyncService
from basic_memory.services.file_service import FileService
from basic_memory.sync.utils import FileChange


class WatchEvent(BaseModel):
    timestamp: datetime
    path: str
    action: str  # sync, delete, etc
    status: str  # success, error
    error: Optional[str] = None


class WatchServiceState(BaseModel):
    # Service status
    running: bool = False
    start_time: datetime = dataclasses.field(default_factory=datetime.now)
    pid: int = dataclasses.field(default_factory=os.getpid)

    # Stats
    files_synced: int = 0
    bytes_processed: int = 0
    error_count: int = 0
    last_error: Optional[datetime] = None
    last_scan: Optional[datetime] = None

    # File counts
    total_files: int = 0
    markdown_files: int = 0

    # Recent activity
    recent_events: List[WatchEvent] = dataclasses.field(default_factory=list)

    def add_event(self, path: str, action: str, status: str, error: Optional[str] = None):
        event = WatchEvent(
            timestamp=datetime.now(), path=path, action=action, status=status, error=error
        )
        self.recent_events.insert(0, event)
        self.recent_events = self.recent_events[:100]  # Keep last 100

    def record_error(self, error: str):
        self.error_count += 1
        self.last_error = datetime.now()


class WatchService:
    def __init__(self, sync_service: SyncService, file_service: FileService, config: ProjectConfig):
        self.sync_service = sync_service
        self.file_service = file_service
        self.config = config
        self.state = WatchServiceState()
        self.status_path = config.home / ".basic-memory" / "watch-status.json"
        self.status_path.parent.mkdir(parents=True, exist_ok=True)

    async def run(self):
        """Watch for file changes and sync them"""
        self.state.running = True
        self.state.start_time = datetime.now()
        await self.write_status()

        try:
            async for changes in awatch(
                self.config.home,
                watch_filter=self.filter_changes,
                debounce=self.config.sync_delay,
                recursive=True,
            ):
                await self.handle_changes(changes)

        except Exception as e:
            self.state.record_error(str(e))
            await self.write_status()
            raise
        finally:
            self.state.running = False
            await self.write_status()

    async def write_status(self):
        """Write current state to status file"""
        self.status_path.write_text(WatchServiceState.model_dump_json(self.state, indent=2))

    def filter_changes(self, change: Change, path: str) -> bool:
        """Filter to only watch markdown files"""
        return path.endswith(".md") and not Path(path).name.startswith(".")

    async def handle_changes(self, changes: set[tuple[Change, str]]):
        """Process a batch of file changes"""

        # Group changes by file path
        changes_by_file = {}
        try:
            for change_type, path in changes:
                file_change = await FileChange.from_path(path, change_type, self.file_service)
                
                # store changes by relative path
                changes_by_file[str(file_change.path)] = file_change

            # Process changes with timeout
            await self.sync_service.sync(file_changes=changes_by_file)

            # Update stats
            self.state.files_synced += len(changes_by_file)
            for path, change in changes_by_file.items():
                if change.change_type != Change.deleted:
                    size = self.file_service.path(path,absolute=True).stat().st_size
                    self.state.bytes_processed += size

                self.state.add_event(path=path, action="sync", status="success")

            await self.write_status()

        except Exception as e:
            self.state.record_error(str(e))
            for path in changes_by_file:
                self.state.add_event(path=path, action="sync", status="error", error=str(e))
            await self.write_status()
            raise
