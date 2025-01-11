"""Command module for basic-memory sync operations."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

import typer
from loguru import logger
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from basic_memory import db
from basic_memory.cli.app import app
from basic_memory.config import config
from basic_memory.db import DatabaseType
from basic_memory.markdown import EntityParser
from basic_memory.repository import (
    EntityRepository,
    ObservationRepository,
    RelationRepository,
)
from basic_memory.repository.search_repository import SearchRepository
from basic_memory.services.search_service import SearchService
from basic_memory.sync import SyncService, FileChangeScanner, EntitySyncService
from basic_memory.sync.utils import SyncReport
from basic_memory.utils.file_utils import ParseError

console = Console()


@dataclass
class ValidationIssue:
    file_path: str
    error: str


async def get_sync_service(db_type=DatabaseType.FILESYSTEM):
    """Get sync service instance with all dependencies."""
    async with db.engine_session_factory(db_path=config.database_path, db_type=db_type) as (
        engine,
        session_maker,
    ):
        # Initialize repositories
        entity_repository = EntityRepository(session_maker)
        observation_repository = ObservationRepository(session_maker)
        relation_repository = RelationRepository(session_maker)
        search_repository = SearchRepository(session_maker)

        # Initialize scanner
        file_change_scanner = FileChangeScanner(entity_repository)

        # Initialize services
        knowledge_sync_service = EntitySyncService(
            entity_repository, observation_repository, relation_repository
        )
        entity_parser = EntityParser(config.home)
        search_service = SearchService(search_repository, entity_repository)

        # Create sync service
        sync_service = SyncService(
            scanner=file_change_scanner,
            entity_sync_service=knowledge_sync_service,
            entity_parser=entity_parser,
            search_service=search_service,
        )

        return sync_service


def group_issues_by_directory(issues: List[ValidationIssue]) -> Dict[str, List[ValidationIssue]]:
    """Group validation issues by directory."""
    grouped = defaultdict(list)
    for issue in issues:
        dir_name = Path(issue.file_path).parent.name
        grouped[dir_name].append(issue)
    return dict(grouped)


def display_validation_errors(issues: List[ValidationIssue]):
    """Display validation errors in a rich, organized format."""
    # Create header
    console.print()
    console.print(
        Panel("[red bold]Error:[/red bold] Invalid frontmatter in knowledge files", expand=False)
    )
    console.print()

    # Group issues by directory
    grouped_issues = group_issues_by_directory(issues)

    # Create tree structure
    tree = Tree("Knowledge Files")
    for dir_name, dir_issues in sorted(grouped_issues.items()):
        # Create branch for directory
        branch = tree.add(
            f"[bold blue]{dir_name}/[/bold blue] " f"([yellow]{len(dir_issues)} files[/yellow])"
        )

        # Add each file issue
        for issue in sorted(dir_issues, key=lambda x: x.file_path):
            file_name = Path(issue.file_path).name
            branch.add(
                Text.assemble(("└─ ", "dim"), (file_name, "yellow"), ": ", (issue.error, "red"))
            )

    # Display tree
    console.print(Padding(tree, (1, 2)))

    # Add help text
    console.print()
    console.print(
        Panel(
            Text.assemble(
                ("To fix:", "bold"),
                "\n1. Add required frontmatter fields to each file",
                "\n2. Run ",
                ("basic-memory sync", "bold cyan"),
                " again",
            ),
            expand=False,
        )
    )
    console.print()


def display_sync_summary(knowledge: SyncReport):
    """Display a one-line summary of sync changes."""
    total_changes = knowledge.total_changes
    if total_changes == 0:
        console.print("[green]Everything up to date[/green]")
        return

    # Format as: "Synced X files (A new, B modified, C deleted)"
    changes = []
    new_count = len(knowledge.new)
    mod_count = len(knowledge.modified)
    del_count = len(knowledge.deleted)

    if new_count:
        changes.append(f"[green]{new_count} new[/green]")
    if mod_count:
        changes.append(f"[yellow]{mod_count} modified[/yellow]")
    if del_count:
        changes.append(f"[red]{del_count} deleted[/red]")

    console.print(f"Synced {total_changes} files ({', '.join(changes)})")


def display_detailed_sync_results(knowledge: SyncReport):
    """Display detailed sync results with trees."""
    if knowledge.total_changes == 0:
        console.print("\n[green]Everything up to date[/green]")
        return

    console.print("\n[bold]Sync Results[/bold]")

    if knowledge.total_changes > 0:
        knowledge_tree = Tree("[bold]Knowledge Files[/bold]")
        if knowledge.new:
            created = knowledge_tree.add("[green]Created[/green]")
            for path in sorted(knowledge.new):
                checksum = knowledge.checksums.get(path, "")
                created.add(f"[green]{path}[/green] ({checksum[:8]})")
        if knowledge.modified:
            modified = knowledge_tree.add("[yellow]Modified[/yellow]")
            for path in sorted(knowledge.modified):
                checksum = knowledge.checksums.get(path, "")
                modified.add(f"[yellow]{path}[/yellow] ({checksum[:8]})")
        if knowledge.deleted:
            deleted = knowledge_tree.add("[red]Deleted[/red]")
            for path in sorted(knowledge.deleted):
                deleted.add(f"[red]{path}[/red]")
        console.print(knowledge_tree)


async def validate_knowledge_files(
    sync_service: SyncService, directory: Path
) -> List[ValidationIssue]:
    """Pre-validate knowledge files and collect all issues."""
    issues = []
    changes = await sync_service.scanner.find_knowledge_changes(directory)

    for file_path in [*changes.new, *changes.modified]:
        try:
            await sync_service.knowledge_parser.parse_file(directory / file_path)
        except ParseError as e:
            issues.append(ValidationIssue(file_path=file_path, error=str(e)))

    return issues


async def run_sync(verbose: bool = False):
    """Run sync operation."""

    sync_service = await get_sync_service()

    # Validate knowledge files before attempting sync
    issues = await validate_knowledge_files(sync_service, config.home)
    if issues:
        display_validation_errors(issues)
        raise typer.Exit(1)

    # Sync
    knowledge_changes = await sync_service.sync(config.home)

    # Display results
    if verbose:
        display_detailed_sync_results(knowledge_changes)
    else:
        display_sync_summary(knowledge_changes)


@app.command()
def sync(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed sync information.",
    ),
) -> None:
    """Sync knowledge files with the database."""
    try:
        # Run sync
        asyncio.run(run_sync(verbose))

    except Exception as e:
        if not isinstance(e, typer.Exit):
            logger.exception("Sync failed")
            typer.echo(f"Error during sync: {e}", err=True)
            raise typer.Exit(1)
        raise
