"""Initialize command for basic-memory CLI."""

import asyncio
from pathlib import Path

import typer
from loguru import logger

from basic_memory.cli.app import app
from basic_memory.db import engine_session_factory, DatabaseType
from basic_memory.config import config


async def _init(force: bool = False):
    """Initialize the database."""
    db_path = config.database_path

    if db_path.exists() and not force:
        typer.echo(f"Database already exists at {db_path}. Use --force to reinitialize.")
        raise typer.Exit(1)
        
    # Create data directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with engine_session_factory(db_path, db_type=DatabaseType.FILESYSTEM, init=True):
            typer.echo(f"Initialized database at {db_path}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        typer.echo(f"Error initializing database: {e}")
        raise typer.Exit(1)

@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialization if database exists")
):
    """Initialize a new basic-memory database."""
    asyncio.run(_init(force))
