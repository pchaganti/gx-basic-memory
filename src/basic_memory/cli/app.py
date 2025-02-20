import asyncio

import typer

from basic_memory import db
from basic_memory.config import config


asyncio.run(db.run_migrations(config))

app = typer.Typer(name="basic-memory")

import_app = typer.Typer()
app.add_typer(import_app, name="import")


claude_app = typer.Typer()
import_app.add_typer(claude_app, name="claude")
