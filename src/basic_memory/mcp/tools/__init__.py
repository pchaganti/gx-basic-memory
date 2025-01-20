"""MCP tools for Basic Memory.

This package provides the complete set of tools for interacting with
Basic Memory through the MCP protocol. Importing this module registers
all tools with the MCP server.
"""

# Import tools to register them with MCP
from basic_memory.mcp.tools.memory import build_context, recent_activity
from basic_memory.mcp.tools.ai_edit import ai_edit

# Export the tools
from basic_memory.mcp.tools.knowledge import (
    create_entities,
    create_relations,
    add_observations,
    delete_entities,
    delete_observations,
    delete_relations,
    get_entity,
    get_entities,
)

__all__ = [
    # Knowledge graph tools
    "create_entities",
    "create_relations",
    "add_observations",
    "delete_entities",
    "delete_observations",
    "delete_relations",
    "get_entity",
    "get_entities",
    # Search tools
    "search",
    # memory tools
    "build_context",
    "recent_activity",
    # file edit
    "ai_edit",
]
