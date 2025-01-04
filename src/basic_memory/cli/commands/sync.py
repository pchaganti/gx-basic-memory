"""Command module for basic-memory sync operations."""
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from collections import defaultdict

import typer
import asyncio
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.padding import Padding
from rich.text import Text
from rich.tree import Tree

from basic_memory.cli.app import app
from basic_memory import db
from basic_memory.config import config
from basic_memory.db import DatabaseType
from basic_memory.repository import DocumentRepository, EntityRepository, ObservationRepository, RelationRepository
from basic_memory.services import (
    DocumentService,
    EntityService, ObservationService, RelationService,
)
from basic_memory.markdown import KnowledgeParser
from basic_memory.services.sync import SyncService, FileChangeScanner, KnowledgeSyncService
from basic_memory.utils.file_utils import ParseError

console = Console()

@dataclass
class ValidationIssue:
    file_path: str
    error: str

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
    console.print(Panel(
        "[red bold]Error:[/red bold] Invalid frontmatter in knowledge files",
        expand=False
    ))
    console.print()

    # Group issues by directory
    grouped_issues = group_issues_by_directory(issues)

    # Create tree structure
    tree = Tree("Knowledge Files")
    for dir_name, dir_issues in sorted(grouped_issues.items()):
        # Create branch for directory
        branch = tree.add(
            f"[bold blue]{dir_name}/[/bold blue] "
            f"([yellow]{len(dir_issues)} files[/yellow])"
        )
        
        # Add each file issue
        for issue in sorted(dir_issues, key=lambda x: x.file_path):
            file_name = Path(issue.file_path).name
            branch.add(
                Text.assemble(
                    ("└─ ", "dim"),
                    (file_name, "yellow"),
                    ": ",
                    (issue.error, "red")
                )
            )

    # Display tree
    console.print(Padding(tree, (1, 2)))
    
    # Add help text
    console.print()
    console.print(Panel(
        Text.assemble(
            ("To fix:", "bold"),
            "\n1. Add required frontmatter fields to each file",
            "\n2. Run ", 
            ("basic-memory sync", "bold cyan"),
            " again"
        ),
        expand=False
    ))
    console.print()


async def get_sync_service(db_type=DatabaseType.FILESYSTEM):
    """Get sync service instance with all dependencies."""
    async with db.engine_session_factory(db_path=config.database_path, db_type=db_type) as (
        engine,
        session_maker,
    ):
        # Initialize repositories
        document_repository = DocumentRepository(session_maker)
        entity_repository = EntityRepository(session_maker)
        observation_repository = ObservationRepository(session_maker)
        relation_repository = RelationRepository(session_maker)

        # Initialize scanner
        file_change_scanner = FileChangeScanner(document_repository, entity_repository)
        
        # Initialize services
        document_service = DocumentService(document_repository, config.documents_dir)
        entity_service = EntityService(entity_repository)
        observation_service = ObservationService(observation_repository)
        relation_service = RelationService(relation_repository)
        
        knowledge_sync_service = KnowledgeSyncService(entity_service, observation_service, relation_service)
        knowledge_parser = KnowledgeParser()

        # Create sync service
        sync_service = SyncService(
            scanner=file_change_scanner,
            document_service=document_service,
            knowledge_sync_service=knowledge_sync_service,
            knowledge_parser=knowledge_parser,
        )
        
        return sync_service


async def validate_knowledge_files(sync_service: SyncService, directory: Path) -> List[ValidationIssue]:
    """Pre-validate knowledge files and collect all issues."""
    issues = []
    changes = await sync_service.scanner.find_knowledge_changes(directory)

    for file_path in [*changes.new, *changes.modified]:
        try:
            await sync_service.knowledge_parser.parse_file(directory / file_path)
        except ParseError as e:
            issues.append(ValidationIssue(file_path=file_path, error=str(e)))

    return issues


async def run_sync():
    """Run sync operation."""
    sync_service = await get_sync_service()

    # Sync documents first
    await sync_service.sync_documents(config.documents_dir)

    # Validate knowledge files before attempting sync
    issues = await validate_knowledge_files(sync_service, config.knowledge_dir)
    if issues:
        display_validation_errors(issues)
        raise typer.Exit(1)
        
    # If validation passes, sync knowledge files
    await sync_service.sync_knowledge(config.knowledge_dir)


@app.command()
def sync(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to sync. Defaults to current project directory.",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed sync information.",
    ),
) -> None:
    """Sync knowledge files with the database.
    
    This command syncs both documents and knowledge files with the database.
    Knowledge files must have required frontmatter fields: type, id, created, modified.
    """
    try:
        # Get project directory
        project_dir = path or Path.cwd()
        logger.info(f"Syncing directory: {project_dir}")

        # Run sync
        asyncio.run(run_sync())

        if verbose:
            logger.info("Sync completed successfully")
    
    except Exception as e:
        if not isinstance(e, typer.Exit):
            logger.exception("Sync failed")
            typer.echo(f"Error during sync: {e}", err=True)
            raise typer.Exit(1)
        raise
