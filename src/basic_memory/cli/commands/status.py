"""Status command for basic-memory CLI."""

import asyncio

import typer
from loguru import logger

from basic_memory import db
from basic_memory.cli.app import app
from basic_memory.config import config
from basic_memory.db import DatabaseType
from basic_memory.repository import DocumentRepository
from basic_memory.services import FileSyncService


async def get_sync_service(db_type=DatabaseType.FILESYSTEM) -> FileSyncService:
    async with db.engine_session_factory(db_path=config.database_path, db_type=db_type) as (
        engine,
        session_maker,
    ):
        document_repository = DocumentRepository(session_maker)
        sync_service = FileSyncService(document_repository)
        return sync_service


@logger.catch
async def run_status(sync_service: FileSyncService = get_sync_service(), verbose: bool = False):
    """Check sync status of files vs database."""

    # Check knowledge/ directory
    typer.echo("\nKnowledge Files:")
    files = await sync_service.scan_files(config.knowledge_dir)
    changes = await sync_service.find_changes(files)

    if changes.total_changes == 0:
        typer.echo("  No changes")
    else:
        if changes.new:
            typer.echo("\n  New files:")
            for f in sorted(changes.new):
                typer.echo(f"    + {f}")
        if changes.modified:
            typer.echo("\n  Modified:")
            for f in sorted(changes.modified):
                typer.echo(f"    * {f}")
        if changes.deleted:
            typer.echo("\n  Deleted:")
            for f in sorted(changes.deleted):
                typer.echo(f"    - {f}")

    # Check documents/ directory
    typer.echo("\nDocuments:")
    files = await sync_service.scan_files(config.documents_dir)
    changes = await sync_service.find_changes(files)

    if changes.total_changes == 0:
        typer.echo("  No changes")
    else:
        if changes.new:
            typer.echo("\n  New files:")
            for f in sorted(changes.new):
                typer.echo(f"    + {f}")
        if changes.modified:
            typer.echo("\n  Modified:")
            for f in sorted(changes.modified):
                typer.echo(f"    * {f}")
        if changes.deleted:
            typer.echo("\n  Deleted:")
            for f in sorted(changes.deleted):
                typer.echo(f"    - {f}")


@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed file information"),
):
    """Show sync status between files and database."""

    sync_service = asyncio.run(get_sync_service())
    asyncio.run(run_status(sync_service, verbose))
