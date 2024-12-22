"""Main CLI entry point for basic-memory"""

import typer

app = typer.Typer()
# app.add_typer(migrate.app, name="migrate")

if __name__ == "__main__":  # pragma: no cover
    app()
