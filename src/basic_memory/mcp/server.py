"""Basic Memory MCP server - simplified proxy to FastAPI endpoints."""

import json
import sys

from httpx import AsyncClient, ASGITransport
from loguru import logger
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    EmbeddedResource,
    TextResourceContents,
    ServerCapabilities,
    ToolsCapability,
)

from basic_memory.api.app import app as fastapi_app

# Create server instance
server = Server("basic-memory")

# Simple map of tool names to endpoints
TOOLS = {
    # Knowledge endpoints
    "create_entities": {"endpoint": "/knowledge/entities/", "method": "post"},
    "search_nodes": {"endpoint": "/knowledge/search/", "method": "post"},
    "open_nodes": {"endpoint": "/knowledge/nodes/", "method": "post"},
    "add_observations": {"endpoint": "/knowledge/observations/", "method": "post"},
    "create_relations": {"endpoint": "/knowledge/relations/", "method": "post"},
    "delete_entities": {"endpoint": "/knowledge/entities/delete/", "method": "post"},
    "delete_observations": {"endpoint": "/knowledge/observations/delete/", "method": "post"},
    "delete_relations": {"endpoint": "/knowledge/relations/delete/", "method": "post"},
    # Document endpoints
    "create_document": {"endpoint": "/documents/", "method": "post"},
    "list_documents": {"endpoint": "/documents/", "method": "get"},
    "get_document": {"endpoint": "/documents/{id}", "method": "get"},
    "update_document": {"endpoint": "/documents/{id}", "method": "put"},
    "delete_document": {"endpoint": "/documents/{id}", "method": "delete"},
}


@server.list_tools()
async def handle_list_tools():
    """Just list our tools with minimal schema."""
    return [
        Tool(name=name, description=f"Call {config['endpoint']}", inputSchema={"type": "object"})
        for name, config in TOOLS.items()
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Simple proxy to FastAPI endpoints."""
    config = TOOLS[name]
    endpoint = config["endpoint"]
    method = config["method"]

    # Handle ID parameter in URL
    if "{id}" in endpoint:
        endpoint = endpoint.format(id=arguments.get("id"))

    # Ensure non-string arguments are properly JSON serialized
    processed_args = {}
    for key, value in arguments.items():
        if key == "doc_metadata" and isinstance(value, str):
            try:
                processed_args[key] = json.loads(value)
            except json.JSONDecodeError:
                processed_args[key] = None
        else:
            processed_args[key] = value

    # Make request to FastAPI
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as client:
        response = await getattr(client, method)(endpoint, json=processed_args)

        # Return wrapped response
        return [
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="basic-memory://response",
                    mimeType="application/json",
                    text=json.dumps(response.json() if response.content else {"status": "success"}),
                ),
            )
        ]


def setup_logging(log_file: str = "basic-memory-mcp.log"):
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()

    # Add file handler with rotation (no colors)
    logger.add(
        log_file,
        rotation="100 MB",
        retention="10 days",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        colorize=False,
    )

    # Add stderr handler for INFO and above (can keep colors here)
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <white>{message}</white>",
        colorize=True,
    )


async def run_server():
    """Run the MCP server with proper initialization."""

    setup_logging()
    logger.info("Starting Basic Memory MCP server")

    # Initialize server with explicit tool capabilities
    options = InitializationOptions(
        server_name="basic-memory",
        server_version="0.1.0",
        capabilities=ServerCapabilities(tools=ToolsCapability(listChanged=True), experimental={}),
    )

    # Run server with proper initialization
    async with stdio_server() as (read, write):
        await server.run(read, write, options)


if __name__ == "__main__":
    from mcp.server.stdio import stdio_server
    import asyncio

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)
