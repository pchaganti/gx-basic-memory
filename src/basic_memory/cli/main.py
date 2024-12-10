"""Main CLI entry point for basic-memory"""
import typer
from . import migrate

app = typer.Typer()
app.add_typer(migrate.app, name="migrate")

if __name__ == "__main__":
    app()