"""Shared MCP instance for Basic Memory."""

from fastmcp import FastMCP
from basic_memory.mcp.tools.enhanced import EnhancedToolManager

# Create and configure the shared MCP instance
mcp = FastMCP("Basic Memory")

# Replace the default tool manager with our enhanced version
mcp._tool_manager = EnhancedToolManager(
    warn_on_duplicate_tools=mcp.settings.warn_on_duplicate_tools
)