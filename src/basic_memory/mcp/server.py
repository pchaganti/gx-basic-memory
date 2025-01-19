"""Enhanced FastMCP server instance for Basic Memory."""
import sys

from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import configure_logging

from basic_memory.config import config

# mcp console logging
configure_logging(level="INFO")


def setup_logging(home_dir: str = config.home, log_file: str = ".basic-memory/basic-memory.log"):
    """Configure file logging to the basic-memory home directory."""
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

    # Add stderr handler
    logger.add(
        sys.stderr,
        colorize=True,
    )

# start our out file logging
setup_logging()

# Create the shared server instance
mcp = FastMCP("Basic Memory")
