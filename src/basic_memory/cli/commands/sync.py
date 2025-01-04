"""Command module for basic-memory sync operations."""

from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import typer
import asyncio
from loguru import logger
from rich.console import Console
from rich.tree import Tree

from basic_memory.cli.app import app
from basic_memory import db
from basic_memory.config import config
from basic_memory.db import DatabaseType
from basic_memory.repository import DocumentRepository, EntityRepository, ObservationRepository, RelationRepository
from basic_memory.services import (
    DocumentService,
    EntityService, ObservationService, RelationService, FileService,
)
from basic_memory.markdown import KnowledgeParser
from basic_memory.services.sync import SyncService, FileChangeScanner, KnowledgeSyncService
from basic_memory.utils.file_utils import ParseError
from basic_memory.services.sync.utils import SyncReport


console = Console()


def display_sync_summary(docs: SyncReport, knowledge: SyncReport):
    """Display a one-line summary of sync changes."""
    total_changes = docs.total_changes + knowledge.total_changes
    if total_changes == 0:
        console.print("[green]Everything up to date[/green]")
        return

    # Format as: "Synced X files (A new, B modified, C deleted)"
    changes = []
    new_count = len(docs.new) + len(knowledge.new)
    mod_count = len(docs.modified) + len(knowledge.modified)
    del_count = len(docs.deleted) + len(knowledge.deleted)

    if new_count:
        changes.append(f"[green]{new_count} new[/green]")
    if mod_count:
        changes.append(f"[yellow]{mod_count} modified[/yellow]")
    if del_count:
        changes.append(f"[red]{del_count} deleted[/red]")

    console.print(f"Synced {total_changes} files ({', '.join(changes)})")


def display_detailed_sync_results(docs: SyncReport, knowledge: SyncReport):
    """Display detailed sync results with trees."""
    if docs.total_changes == 0 and knowledge.total_changes == 0:
        console.print("\n[green]Everything up to date[/green]")
        return

    console.print("\n[bold]Sync Results[/bold]")

    if docs.total_changes > 0:
        doc_tree = Tree("[bold]Documents[/bold]")
        if docs.new:
            created = doc_tree.add("[green]Created[/green]")
            for path in sorted(docs.new):
                checksum = docs.checksums.get(path, '')
                created.add(f"[green]{path}[/green] ({checksum[:8]})")
        if docs.modified:
            modified = doc_tree.add("[yellow]Modified[/yellow]")
            for path in sorted(docs.modified):
                checksum = docs.checksums.get(path, '')
                modified.add(f"[yellow]{path}[/yellow] ({checksum[:8]})")
        if docs.deleted:
            deleted = doc_tree.add("[red]Deleted[/red]")
            for path in sorted(docs.deleted):
                deleted.add(f"[red]{path}[/red]")
        console.print(doc_tree)

    if knowledge.total_changes > 0:
        knowledge_tree = Tree("[bold]Knowledge Files[/bold]")
        if knowledge.new:
            created = knowledge_tree.add("[green]Created[/green]")
            for path in sorted(knowledge.new):
                checksum = knowledge.checksums.get(path, '')
                created.add(f"[green]{path}[/green] ({checksum[:8]})")
        if knowledge.modified:
            modified = knowledge_tree.add("[yellow]Modified[/yellow]")
            for path in sorted(knowledge.modified):
                checksum = knowledge.checksums.get(path, '')
                modified.add(f"[yellow]{path}[/yellow] ({checksum[:8]})")
        if knowledge.deleted:
            deleted = knowledge_tree.add("[red]Deleted[/red]")
            for path in sorted(knowledge.deleted):
                deleted.add(f"[red]{path}[/red]")
        console.print(knowledge_tree)


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
        document_service = DocumentService(document_repository, config.documents_dir, FileService())
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


async def run_sync(verbose: bool = False):
    """Run sync operation."""
    sync_service = await get_sync_service()

    # Scan for changes first
    doc_changes = None
    knowledge_changes = None

    if config.documents_dir.exists():
        doc_changes = await sync_service.scanner.find_document_changes(config.documents_dir)
        await sync_service.sync_documents(config.documents_dir)

    if config.knowledge_dir.exists():
        knowledge_changes = await sync_service.scanner.find_knowledge_changes(config.knowledge_dir)
        await sync_service.sync_knowledge(config.knowledge_dir)

    # Use empty reports if directories don't exist
    doc_changes = doc_changes or SyncReport()
    knowledge_changes = knowledge_changes or SyncReport()

    # Display results
    if verbose:
        display_detailed_sync_results(doc_changes, knowledge_changes)
    else:
        display_sync_summary(doc_changes, knowledge_changes)


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
        # Run sync
        asyncio.run(run_sync(verbose))
    
    except Exception as e:
        if not isinstance(e, typer.Exit):
            logger.exception("Sync failed")
            typer.echo(f"Error during sync: {e}", err=True)
            raise typer.Exit(1)
        raise