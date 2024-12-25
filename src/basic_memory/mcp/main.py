"""Main MCP entrypoint for Basic Memory.

Creates and configures the shared MCP instance and handles server startup.
"""

import sys
from loguru import logger

# Import shared mcp instance
from basic_memory.mcp.server import mcp

# Import tools to register them
from basic_memory.mcp.tools import knowledge, search, documents
__all__ = ["mcp", "knowledge", "search", "documents"]


def setup_logging(log_file: str = "basic-memory-mcp.log"):
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()

    # Add file handler with rotation
    logger.add(
        log_file,
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
    setup_logging()
    logger.info("Starting Basic Memory MCP server")
    mcp.run()