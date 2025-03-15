"""Watch service for Basic Memory."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from basic_memory.config import ProjectConfig
from basic_memory.services.file_service import FileService
from basic_memory.sync.sync_service import SyncService
from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from watchfiles import awatch
from watchfiles.main import FileChange, Change

WATCH_STATUS_JSON = "watch-status.json"


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
    start_time: datetime = datetime.now()  # Use directly with Pydantic model
    pid: int = os.getpid()  # Use directly with Pydantic model

    # Stats
    error_count: int = 0
    last_error: Optional[datetime] = None
    last_scan: Optional[datetime] = None

    # File counts
    synced_files: int = 0

    # Recent activity
    recent_events: List[WatchEvent] = []  # Use directly with Pydantic model

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
        self.status_path = config.home / ".basic-memory" / WATCH_STATUS_JSON
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.console = Console()

    async def run(self):  # pragma: no cover
        """Watch for file changes and sync them"""
        logger.info(
            "Watch service started",
            directory=str(self.config.home),
            debounce_ms=self.config.sync_delay,
            pid=os.getpid(),
        )

        self.state.running = True
        self.state.start_time = datetime.now()
        await self.write_status()

        try:
            async for changes in awatch(
                self.config.home,
                debounce=self.config.sync_delay,
                watch_filter=self.filter_changes,
                recursive=True,
            ):
                await self.handle_changes(self.config.home, changes)

        except Exception as e:
            logger.exception("Watch service error", error=str(e), directory=str(self.config.home))

            self.state.record_error(str(e))
            await self.write_status()
            raise

        finally:
            logger.info(
                "Watch service stopped",
                directory=str(self.config.home),
                runtime_seconds=int((datetime.now() - self.state.start_time).total_seconds()),
            )

            self.state.running = False
            await self.write_status()

    def filter_changes(self, change: Change, path: str) -> bool:  # pragma: no cover
        """Filter to only watch non-hidden files and directories.

        Returns:
            True if the file should be watched, False if it should be ignored
        """
        # Skip if path is invalid
        try:
            relative_path = Path(path).relative_to(self.config.home)
        except ValueError:
            # This is a defensive check for paths outside our home directory
            return False

        # Skip hidden directories and files
        path_parts = relative_path.parts
        for part in path_parts:
            if part.startswith("."):
                return False

        # Skip temp files used in atomic operations
        if path.endswith(".tmp"):
            return False

        return True

    async def write_status(self):
        """Write current state to status file"""
        self.status_path.write_text(WatchServiceState.model_dump_json(self.state, indent=2))

    async def handle_changes(self, directory: Path, changes: Set[FileChange]):
        """Process a batch of file changes"""
        import time
        from typing import List, Set

        start_time = time.time()

        logger.info("Processing file changes", change_count=len(changes), directory=str(directory))

        # Group changes by type
        adds: List[str] = []
        deletes: List[str] = []
        modifies: List[str] = []

        for change, path in changes:
            # convert to relative path
            relative_path = str(Path(path).relative_to(directory))

            # Skip .tmp files - they're temporary and shouldn't be synced
            if relative_path.endswith(".tmp"):
                continue

            if change == Change.added:
                adds.append(relative_path)
            elif change == Change.deleted:
                deletes.append(relative_path)
            elif change == Change.modified:
                modifies.append(relative_path)

        logger.debug(
            "Grouped file changes", added=len(adds), deleted=len(deletes), modified=len(modifies)
        )

        # Track processed files to avoid duplicates
        processed: Set[str] = set()

        # First handle potential moves
        for added_path in adds:
            if added_path in processed:
                continue  # pragma: no cover

            # Skip directories for added paths
            # We don't need to process directories, only the files inside them
            # This prevents errors when trying to compute checksums or read directories as files
            added_full_path = directory / added_path
            if not added_full_path.exists() or added_full_path.is_dir():
                logger.debug("Skipping non-existent or directory path", path=added_path)
                processed.add(added_path)
                continue

            for deleted_path in deletes:
                if deleted_path in processed:
                    continue  # pragma: no cover

                # Skip directories for deleted paths (based on entity type in db)
                deleted_entity = await self.sync_service.entity_repository.get_by_file_path(
                    deleted_path
                )
                if deleted_entity is None:
                    # If this was a directory, it wouldn't have an entity
                    logger.debug("Skipping unknown path for move detection", path=deleted_path)
                    continue

                if added_path != deleted_path:
                    # Compare checksums to detect moves
                    try:
                        added_checksum = await self.file_service.compute_checksum(added_path)

                        if deleted_entity and deleted_entity.checksum == added_checksum:
                            await self.sync_service.handle_move(deleted_path, added_path)
                            self.state.add_event(
                                path=f"{deleted_path} -> {added_path}",
                                action="moved",
                                status="success",
                            )
                            self.console.print(f"[blue]→[/blue] {deleted_path} → {added_path}")
                            processed.add(added_path)
                            processed.add(deleted_path)
                            break
                    except Exception as e:  # pragma: no cover
                        logger.warning(
                            "Error checking for move",
                            old_path=deleted_path,
                            new_path=added_path,
                            error=str(e),
                        )

        # Handle remaining changes - group them by type for concise output
        moved_count = len([p for p in processed if p in deletes or p in adds])
        delete_count = 0
        add_count = 0
        modify_count = 0

        # Process deletes
        for path in deletes:
            if path not in processed:
                logger.debug("Processing deleted file", path=path)
                await self.sync_service.handle_delete(path)
                self.state.add_event(path=path, action="deleted", status="success")
                self.console.print(f"[red]✕[/red] {path}")
                processed.add(path)
                delete_count += 1

        # Process adds
        for path in adds:
            if path not in processed:
                # Skip directories - only process files
                full_path = directory / path
                if not full_path.exists() or full_path.is_dir():
                    logger.debug(
                        "Skipping non-existent or directory path", path=path
                    )  # pragma: no cover
                    processed.add(path)  # pragma: no cover
                    continue  # pragma: no cover

                logger.debug("Processing new file", path=path)
                entity, checksum = await self.sync_service.sync_file(path, new=True)
                if checksum:
                    self.state.add_event(
                        path=path, action="new", status="success", checksum=checksum
                    )
                    self.console.print(f"[green]✓[/green] {path}")
                    logger.debug(
                        "Added file processed",
                        path=path,
                        entity_id=entity.id if entity else None,
                        checksum=checksum,
                    )
                    processed.add(path)
                    add_count += 1
                else:  # pragma: no cover
                    logger.warning("Error syncing new file", path=path)  # pragma: no cover
                    self.console.print(
                        f"[orange]?[/orange] Error syncing: {path}"
                    )  # pragma: no cover

        # Process modifies - detect repeats
        last_modified_path = None
        repeat_count = 0

        for path in modifies:
            if path not in processed:
                # Skip directories - only process files
                full_path = directory / path
                if not full_path.exists() or full_path.is_dir():
                    logger.debug("Skipping non-existent or directory path", path=path)
                    processed.add(path)
                    continue

                logger.debug("Processing modified file", path=path)
                entity, checksum = await self.sync_service.sync_file(path, new=False)
                self.state.add_event(
                    path=path, action="modified", status="success", checksum=checksum
                )

                # Check if this is a repeat of the last modified file
                if path == last_modified_path:  # pragma: no cover
                    repeat_count += 1  # pragma: no cover
                    # Only show a message for the first repeat
                    if repeat_count == 1:  # pragma: no cover
                        self.console.print(
                            f"[yellow]...[/yellow] Repeated changes to {path}"
                        )  # pragma: no cover
                else:
                    # New file being modified
                    self.console.print(f"[yellow]✎[/yellow] {path}")
                    last_modified_path = path
                    repeat_count = 0
                    modify_count += 1

                logger.debug(
                    "Modified file processed",
                    path=path,
                    entity_id=entity.id if entity else None,
                    checksum=checksum,
                )
                processed.add(path)

        # Add a concise summary instead of a divider
        if processed:
            changes = []  # pyright: ignore
            if add_count > 0:
                changes.append(f"[green]{add_count} added[/green]")  # pyright: ignore
            if modify_count > 0:
                changes.append(f"[yellow]{modify_count} modified[/yellow]")  # pyright: ignore
            if moved_count > 0:
                changes.append(f"[blue]{moved_count} moved[/blue]")  # pyright: ignore
            if delete_count > 0:
                changes.append(f"[red]{delete_count} deleted[/red]")  # pyright: ignore

            if changes:
                self.console.print(f"{', '.join(changes)}", style="dim")  # pyright: ignore

        duration_ms = int((time.time() - start_time) * 1000)
        self.state.last_scan = datetime.now()
        self.state.synced_files += len(processed)

        logger.info(
            "File change processing completed",
            processed_files=len(processed),
            total_synced_files=self.state.synced_files,
            duration_ms=duration_ms,
        )

        await self.write_status()