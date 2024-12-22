"""Basic Memory MCP server implementation.

Creates a server that handles MCP tool calls and forwards them to our FastAPI endpoints.
Uses proper lifecycle management and logging to ensure reliable operation.
"""

import asyncio
import json
import sys
from typing import List, Dict, Any

from httpx import AsyncClient, ASGITransport
from loguru import logger
from mcp import McpError
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    EmbeddedResource,
    TextResourceContents,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    ServerCapabilities,
    ToolsCapability,
)
from pydantic import TypeAdapter, AnyUrl

from basic_memory.api.app import app as fastapi_app
from basic_memory.schemas import (
    CreateEntityRequest,
    SearchNodesRequest,
    OpenNodesRequest,
    AddObservationsRequest,
    CreateRelationsRequest,
    DeleteEntitiesRequest,
    DeleteObservationsRequest,
    DeleteRelationsRequest,
)

BASE_URL = "http://test"

# URI constants
url_validator = TypeAdapter(AnyUrl)
BASIC_MEMORY_URI = url_validator.validate_python("basic-memory://response")
MIME_TYPE = "application/vnd.basic-memory+json"

# Create server instance
server = Server("basic-memory")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Define the available tools."""
    logger.debug("Listing available tools")
    return [
        Tool(
            name="create_entities",
            description="Create multiple new entities",
            inputSchema=CreateEntityRequest.model_json_schema(),
        ),
        Tool(
            name="search_nodes",
            description="Search for nodes",
            inputSchema=SearchNodesRequest.model_json_schema(),
        ),
        Tool(
            name="open_nodes",
            description="Open specific nodes",
            inputSchema=OpenNodesRequest.model_json_schema(),
        ),
        Tool(
            name="add_observations",
            description="Add observations",
            inputSchema=AddObservationsRequest.model_json_schema(),
        ),
        Tool(
            name="create_relations",
            description="Create relations",
            inputSchema=CreateRelationsRequest.model_json_schema(),
        ),
        Tool(
            name="delete_entities",
            description="Delete entities",
            inputSchema=DeleteEntitiesRequest.model_json_schema(),
        ),
        Tool(
            name="delete_observations",
            description="Delete observations",
            inputSchema=DeleteObservationsRequest.model_json_schema(),
        ),
        Tool(
            name="delete_relations",
            description="Delete relations",
            inputSchema=DeleteRelationsRequest.model_json_schema(),
        ),
    ]


async def call_tool_endpoint(endpoint: str, json: dict[str, Any]):
    """Makes a request to a FastAPI endpoint with a fresh client."""
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url=BASE_URL, timeout=30.0
    ) as client:
        logger.debug(f"Calling API endpoint {endpoint} with arguments: {json}")
        response = await client.post(endpoint, json=json)
        logger.debug(response.json())
        return response


def create_response(data: Dict[str, Any]) -> EmbeddedResource:
    """Create standard MCP response wrapper."""
    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=BASIC_MEMORY_URI,
            mimeType=MIME_TYPE,
            text=json.dumps(data),
        ),
    )


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[EmbeddedResource]:
    """Forward tool calls to FastAPI endpoints."""

    try:
        logger.info(f"Tool call: {name}")
        logger.debug(f"Arguments: {arguments}")

        # Map tools to FastAPI endpoints
        handlers = {
            "create_entities": "/knowledge/entities",
            "search_nodes": "/knowledge/search",
            "open_nodes": "/knowledge/nodes",
            "add_observations": "/knowledge/observations",
            "create_relations": "/knowledge/relations",
            "delete_entities": "/knowledge/entities/delete",
            "delete_observations": "/knowledge/observations/delete",
            "delete_relations": "/knowledge/relations/delete",
        }

        # Get handler for tool
        endpoint = handlers.get(name)
        if endpoint is None:
            raise McpError(METHOD_NOT_FOUND, f"Unknown tool: {name}")

        # Make API call
        response = await call_tool_endpoint(endpoint, arguments)

        # Handle HTTP errors
        if response.status_code >= 400:
            error_data = response.json()
            if response.status_code == 404:
                raise McpError(METHOD_NOT_FOUND, error_data.get("detail", "Not found"))
            elif response.status_code == 422:
                raise McpError(INVALID_PARAMS, error_data.get("detail", "Invalid parameters"))
            else:
                raise McpError(INTERNAL_ERROR, error_data.get("detail", "Internal error"))

        # Create response
        result = create_response(response.json())
        logger.debug(f"Tool call successful: {result}")
        return [result]

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise McpError(INVALID_PARAMS, str(e))
    except Exception as e:
        logger.error(f"Error handling tool call: {e}")
        if isinstance(e, McpError):
            raise
        raise McpError(INTERNAL_ERROR, str(e))


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
    """Run the MCP server with proper initialization and cleanup."""
    setup_logging()
    logger.info("Starting Basic Memory MCP server")

    try:
        # Initialize server with explicit tool capabilities
        options = InitializationOptions(
            server_name="basic-memory",
            server_version="0.1.0",
            capabilities=ServerCapabilities(
                tools=ToolsCapability(listChanged=True),  # Explicitly enable tools
                experimental={},
            ),
        )
        logger.debug(f"Server initialization options: {options}")

        # Run server
        logger.info("Server initialized, waiting for client connection")
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("STDIO streams established")
            await server.run(read_stream, write_stream, options)

    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Server shutting down")


if __name__ == "__main__":
    from mcp.server.stdio import stdio_server

    # Run with proper asyncio error handling
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {e}")
        sys.exit(1)
