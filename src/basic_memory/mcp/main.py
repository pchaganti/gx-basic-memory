"""Main MCP entrypoint for Basic Memory.

Creates and configures the shared MCP instance and handles server startup.
"""

from loguru import logger

from basic_memory.config import config

# Import shared mcp instance
from basic_memory.mcp.server import mcp

# Import tools to register them
import basic_memory.mcp.tools  # noqa: F401


if __name__ == "__main__":
    home_dir = config.home
    logger.info("Starting Basic Memory MCP server")
    logger.info(f"Home directory: {home_dir}")
    mcp.run()
