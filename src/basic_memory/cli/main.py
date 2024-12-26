"""Main CLI entry point for basic-memory"""

import asyncio
from pathlib import Path

import typer

from basic_memory.db import engine_session_factory, DatabaseType

app = typer.Typer()

@app.command()
def init_db(
    project_path: str = typer.Argument(..., help="Path to project directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialization if database exists")
):
    """Initialize a new project database."""
    async def _init_db():
        path = Path(project_path)
        db_path = path / "data" / "memory.db"

        if db_path.exists() and not force:
            typer.echo(f"Database already exists at {db_path}. Use --force to reinitialize.")
            raise typer.Exit(1)
            
        # Create data directory if needed
        db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with engine_session_factory(db_path, db_type=DatabaseType.FILESYSTEM, init=True):
                typer.echo(f"Initialized database at {db_path}")
        except Exception as e:
            typer.echo(f"Error initializing database: {e}")
            raise typer.Exit(1)

    asyncio.run(_init_db())

@app.command()
def hello(name: str):
    print(f"Hello {name}")
    
if __name__ == "__main__":  # pragma: no cover
    app()