"""Command module for basic-memory sync operations."""
from pathlib import Path
from typing import Optional

import typer
import asyncio
from loguru import logger

from basic_memory.cli.app import app
from basic_memory import db
from basic_memory.config import config
from basic_memory.db import DatabaseType
from basic_memory.repository import DocumentRepository, EntityRepository
from basic_memory.services import (
    DocumentService,
    EntityService,
)
from basic_memory.markdown import KnowledgeParser
from basic_memory.services.sync import SyncService, FileChangeScanner, KnowledgeSyncService


async def get_sync_service(db_type=DatabaseType.FILESYSTEM):
    """Get sync service instance with all dependencies."""
    async with db.engine_session_factory(db_path=config.database_path, db_type=db_type) as (
        engine,
        session_maker,
    ):
        # Initialize repositories
        document_repository = DocumentRepository(session_maker)
        entity_repository = EntityRepository(session_maker)

        # Initialize scanner
        file_change_scanner = FileChangeScanner(document_repository, entity_repository)
        
        # Initialize services
        document_service = DocumentService(document_repository)
        entity_service = EntityService(entity_repository)
        knowledge_sync_service = KnowledgeSyncService(entity_service)
        knowledge_parser = KnowledgeParser()

        # Create sync service
        sync_service = SyncService(
            scanner=file_change_scanner,
            document_service=document_service,
            knowledge_sync_service=knowledge_sync_service,
            knowledge_parser=knowledge_parser,
        )
        
        return sync_service


async def run_sync(root_dir: Path):
    """Run sync operation."""
    sync_service = await get_sync_service()
    await sync_service.sync(root_dir)


@app.command()
def sync(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed sync information.",
    ),
) -> None:
    """Sync knowledge files with the database.
    
    This command syncs both documents and knowledge files with the database,
    using a two-pass strategy for knowledge files to handle relations correctly.
    
    Use 'basic-memory status' to preview changes before syncing.
    """
    try:
        # Get project directory
        project_dir = config.home
        logger.info(f"Syncing directory: {project_dir}")

        # Run sync
        asyncio.run(run_sync(project_dir))

        if verbose:
            logger.info("Sync completed successfully")
    
    except Exception as e:
        logger.exception(f"Sync failed: {e}")
        typer.echo(f"Error during sync: {e}", err=True)
        raise typer.Exit(1)
