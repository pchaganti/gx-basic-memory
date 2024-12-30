"""Main MCP entrypoint for Basic Memory.

Creates and configures the shared MCP instance and handles server startup.
"""

import sys
from loguru import logger

from basic_memory.config import config
# Import shared mcp instance
from basic_memory.mcp.server import mcp

# Import tools to register them
from basic_memory.mcp.tools import knowledge, search, documents, discovery
__all__ = ["mcp", "knowledge", "search", "documents", "discovery"]


def setup_logging(home_dir: str = config.home, log_file: str = "basic-memory.log"):
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

    # Add stderr handler
    logger.add(
        sys.stderr,
        colorize=True,
    )


if __name__ == "__main__":
    
    home_dir = config.home
    setup_logging(home_dir)
    logger.info("Starting Basic Memory MCP server")
    logger.info(f"Home directory: {home_dir}" )
    mcp.run()