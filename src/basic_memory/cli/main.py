"""Main CLI entry point for basic-memory."""

import typer

from basic_memory.cli.app import app
from basic_memory.cli.commands.init import init

# Register commands
from basic_memory.cli.commands import init
__all__ = ["init"]


if __name__ == "__main__":  # pragma: no cover
    app()
