"""Main CLI entry point for basic-memory."""

import typer
from loguru import logger

from basic_memory.cli.app import app
from basic_memory.cli.commands.init import init

# Register commands
from basic_memory.cli.commands import init
__all__ = ["init"]

from basic_memory.config import config


def setup_logging(home_dir: str = config.home, log_file: str = "basic-memory-tools.log"):
    """Configure logging for the application."""
    
    # Remove default handler
    logger.remove()
    log = f"{home_dir}/{log_file}"

    # Add file handler with rotation
    logger.add(
        log,
        rotation="100 MB",
        retention="10 days",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        colorize=False,
    )


if __name__ == "__main__":  # pragma: no cover
    setup_logging()
    app()
