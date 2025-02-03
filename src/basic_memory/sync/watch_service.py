"""Watch service for Basic Memory."""

import dataclasses

from loguru import logger
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from watchfiles import awatch, Change
import os

from basic_memory.config import ProjectConfig
from basic_memory.sync.sync_service import SyncService
from basic_memory.services.file_service import FileService

console = Console()


class WatchEvent(BaseModel):
    timestamp: datetime
    path: str
    action: str  # new, delete, etc
    status: str  # success, error
    checksum: Optional[str]
    error: Optional[str] = None


class WatchServiceState(BaseModel):
    # Service status
    running: bool = False
    start_time: datetime = dataclasses.field(default_factory=datetime.now)
    pid: int = dataclasses.field(default_factory=os.getpid)

    # Stats
    error_count: int = 0
    last_error: Optional[datetime] = None
    last_scan: Optional[datetime] = None

    # File counts
    synced_files: int = 0

    # Recent activity
    recent_events: List[WatchEvent] = dataclasses.field(default_factory=list)

    def add_event(
        self,
        path: str,
        action: str,
        status: str,
        checksum: Optional[str] = None,
        error: Optional[str] = None,
    ) -> WatchEvent:
        event = WatchEvent(
            timestamp=datetime.now(),
            path=path,
            action=action,
            status=status,
            checksum=checksum,
            error=error,
        )
        self.recent_events.insert(0, event)
        self.recent_events = self.recent_events[:100]  # Keep last 100
        return event

    def record_error(self, error: str):
        self.error_count += 1
        self.add_event(path="", action="sync", status="error", error=error)
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

        console.print("\n[cyan]Watching for changes...[/cyan]")
        try:
            async for changes in awatch(
                self.config.home,
                watch_filter=self.filter_changes,
                debounce=self.config.sync_delay,
                recursive=True,
            ):
                # just sync the whole dir
                await self.handle_changes(self.config.home)

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

    async def handle_changes(self, directory: Path):
        """Process a batch of file changes"""

        logger.debug(f"handling change in directory: {directory} ...")
        # Process changes with timeout
        report = await self.sync_service.sync(directory)
        self.state.last_scan = datetime.now()
        self.state.synced_files = report.total

        # Update stats
        for path in report.new:
            event = self.state.add_event(
                path=path, action="new", status="success", checksum=report.checksums[path]
            )
            console.print(
                f"{event.timestamp.isoformat(timespec='minutes')} New:\t\t [green]{path}[/green] ({event.checksum[:8]})"
            )
        for path in report.modified:
            event = self.state.add_event(
                path=path, action="modified", status="success", checksum=report.checksums[path]
            )
            console.print(
                f"{event.timestamp.isoformat(timespec='minutes')} Modified:\t [yellow]{path}[/yellow] ({event.checksum[:8]})"
            )
        for old_path, new_path in report.moves.items():
            event = self.state.add_event(
                path=f"{old_path} -> {new_path}",
                action="moved",
                status="success",
                checksum=report.checksums[new_path],
            )
            console.print(
                f"{event.timestamp.isoformat(timespec='minutes')} Moved:\t\t [blue]{old_path} -> {new_path}[/blue] ({event.checksum[:8]})"
            )
        for path in report.deleted:
            event = self.state.add_event(path=path, action="deleted", status="success")
            console.print(f"{event.timestamp.isoformat(timespec='minutes')} Deleted:\t [red]{path}[/red]")

        await self.write_status()
