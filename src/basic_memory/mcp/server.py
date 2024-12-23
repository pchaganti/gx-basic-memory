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
from pydantic import TypeAdapter, AnyUrl, ValidationError

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
    DocumentCreateRequest,
    DocumentUpdateRequest,
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
        # Knowledge graph tools
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
        # Document tools
        Tool(
            name="create_document",
            description="Create a new document",
            inputSchema=DocumentCreateRequest.model_json_schema(),
        ),
        Tool(
            name="list_documents",
            description="List all documents",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_document",
            description="Get a document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Document ID"
                    },
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="update_document",
            description="Update a document by ID",
            inputSchema=DocumentUpdateRequest.model_json_schema(),
        ),
        Tool(
            name="delete_document",
            description="Delete a document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Document ID"
                    },
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        ),
    ]


async def call_tool_endpoint(endpoint: str, json: dict[str, Any], method: str = "post"):
    """Makes a request to a FastAPI endpoint with a fresh client."""
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url=BASE_URL, timeout=30.0
    ) as client:
        logger.debug(f"Calling API endpoint {endpoint} with {method}: {json}")
        try:
            if method == "post":
                response = await client.post(endpoint, json=json)
            elif method == "get":
                # For GET requests, don't send body
                params = {k:v for k,v in json.items() if k != "id"}
                response = await client.get(endpoint, params=params)
            elif method == "put":
                response = await client.put(endpoint, json=json)
            elif method == "delete":
                response = await client.delete(endpoint)
            logger.debug(response.json() if response.content else "No content")
            return response
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise McpError(INVALID_PARAMS, str(e))


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

        # Map tools to FastAPI endpoints and methods
        handlers = {
            # Knowledge graph endpoints
            "create_entities": ("/knowledge/entities", "post"),
            "search_nodes": ("/knowledge/search", "post"),
            "open_nodes": ("/knowledge/nodes", "post"),
            "add_observations": ("/knowledge/observations", "post"),
            "create_relations": ("/knowledge/relations", "post"),
            "delete_entities": ("/knowledge/entities/delete", "post"),
            "delete_observations": ("/knowledge/observations/delete", "post"),
            "delete_relations": ("/knowledge/relations/delete", "post"),
            # Document endpoints
            "create_document": ("/documents", "post"),
            "list_documents": ("/documents", "get"),
            "get_document": ("/documents/{id}", "get"),
            "update_document": ("/documents/{id}", "put"),
            "delete_document": ("/documents/{id}", "delete"),
        }

        # Get handler for tool
        handler = handlers.get(name)
        if handler is None:
            raise McpError(METHOD_NOT_FOUND, f"Unknown tool: {name}")

        endpoint, method = handler

        # Validate tool arguments for common fields
        if "id" in arguments:
            if not isinstance(arguments["id"], int):
                raise McpError(INVALID_PARAMS, "ID must be an integer")
            if arguments["id"] < 1:
                raise McpError(INVALID_PARAMS, "ID must be greater than 0")

        if name == "create_document" and (
            "path" not in arguments or 
            "content" not in arguments
        ):
            raise McpError(INVALID_PARAMS, "Document creation requires path and content")

        if name == "update_document" and (
            "content" not in arguments or
            "id" not in arguments
        ):
            raise McpError(INVALID_PARAMS, "Document update requires content and ID")

        # Format endpoint for ID-based routes
        if "{id}" in endpoint:
            id = arguments.get("id")
            if id is None:
                raise McpError(INVALID_PARAMS, "ID parameter required")
            endpoint = endpoint.format(id=id)

        # Make API call
        response = await call_tool_endpoint(endpoint, arguments, method)

        # Handle HTTP errors
        if response.status_code >= 400:
            error_data = response.json()
            error_detail = error_data.get("detail", "")
            
            # For validation errors, always raise INVALID_PARAMS
            if response.status_code == 422:
                raise McpError(INVALID_PARAMS, error_detail)
            # For document not found, use INVALID_PARAMS
            elif response.status_code == 404 and "Document not found" in str(error_detail):
                raise McpError(INVALID_PARAMS, error_detail)
            # For other 404s, use METHOD_NOT_FOUND
            elif response.status_code == 404:
                raise McpError(METHOD_NOT_FOUND, error_detail or "Not found")
            else:
                raise McpError(INTERNAL_ERROR, error_detail or "Internal error")

        # Create response
        if response.content:  # Some endpoints (like DELETE) return no content
            result = create_response(response.json())
        else:
            result = create_response({"status": "success"})

        logger.debug(f"Tool call successful: {result}")
        return [result]

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise McpError(INVALID_PARAMS, str(e))
    except ValueError as e:
        logger.error(f"Value error: {e}")
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