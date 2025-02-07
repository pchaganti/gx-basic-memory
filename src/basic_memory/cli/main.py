"""Main CLI entry point for basic-memory."""
import sys

import typer
from loguru import logger

from basic_memory.cli.app import app

# Register commands
from basic_memory.cli.commands import status, sync
__all__ = ["status", "sync"]

from basic_memory.config import config


def setup_logging(home_dir: str = config.home, log_file: str = ".basic-memory/basic-memory-tools.log"):
    """Configure logging for the application."""

    # Remove default handler and any existing handlers
    logger.remove()

    # Add file handler for debug level logs
    log = f"{home_dir}/{log_file}"
    logger.add(
        log,
        level="DEBUG",
        rotation="100 MB",
        retention="10 days",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        colorize=False,
    )

    # Add stderr handler for warnings and errors only
    logger.add(
        sys.stderr,
        level="WARNING",
        backtrace=True,
        diagnose=True
    )

# Set up logging when module is imported
setup_logging()

if __name__ == "__main__":  # pragma: no cover
    app()
