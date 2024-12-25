"""MCP tools for Basic Memory.

This package provides the complete set of tools for interacting with
Basic Memory through the MCP protocol. Importing this module registers
all tools with the MCP server.
"""

# Import tools to register them with MCP
from basic_memory.mcp.tools import knowledge  # noqa: F401
from basic_memory.mcp.tools import search     # noqa: F401
from basic_memory.mcp.tools import documents  # noqa: F401

# Export the tools
from basic_memory.mcp.tools.knowledge import (
    create_entities,
    create_relations,
    add_observations,
    delete_entities,
    delete_observations,
    delete_relations,
    get_entity,
)

from basic_memory.mcp.tools.search import (
    search_nodes,
    open_nodes,
)

from basic_memory.mcp.tools.documents import (
    create_document,
    get_document,
    update_document,
    list_documents,
    delete_document,
)

__all__ = [
    # Knowledge graph tools
    "create_entities",
    "create_relations", 
    "add_observations",
    "delete_entities",
    "delete_observations",
    "delete_relations",

    # Search tools
    "search_nodes",
    "get_entity",
    "open_nodes",

    # Document tools
    "create_document",
    "get_document",
    "update_document",
    "list_documents",
    "delete_document",
]