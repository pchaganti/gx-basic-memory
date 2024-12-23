"""Basic Memory MCP server implementation.

Creates a server that handles MCP tool calls and forwards them to our FastAPI endpoints.
Uses proper lifecycle management and logging to ensure reliable operation.
"""

import asyncio
import json
import sys
from typing import List, Dict, Any, Optional

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
from pydantic import TypeAdapter, AnyUrl, ValidationError, BaseModel, Field, constr

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


class IdRequest(BaseModel):
    """Validates ID parameters."""
    id: int = Field(gt=0, description="Resource ID")


class DocumentRequest(BaseModel):
    """Validates document creation."""
    path: constr(min_length=1) = Field(..., description="Document path")
    content: str = Field(..., description="Document content")
    doc_metadata: Optional[Dict[str, Any]] = Field(None, description="Optional document metadata")


# Tool definitions with schemas and endpoints
TOOLS = {
    # Knowledge graph tools
    "create_entities": {
        "schema": CreateEntityRequest,
        "endpoint": "/knowledge/entities",
        "method": "post",
        "description": "Create multiple new entities",
    },
    "search_nodes": {
        "schema": SearchNodesRequest,
        "endpoint": "/knowledge/search",
        "method": "post",
        "description": "Search for nodes",
    },
    "open_nodes": {
        "schema": OpenNodesRequest,
        "endpoint": "/knowledge/nodes",
        "method": "post",
        "description": "Open specific nodes",
    },
    "add_observations": {
        "schema": AddObservationsRequest,
        "endpoint": "/knowledge/observations",
        "method": "post",
        "description": "Add observations",
    },
    "create_relations": {
        "schema": CreateRelationsRequest,
        "endpoint": "/knowledge/relations",
        "method": "post",
        "description": "Create relations",
    },
    "delete_entities": {
        "schema": DeleteEntitiesRequest,
        "endpoint": "/knowledge/entities/delete",
        "method": "post",
        "description": "Delete entities",
    },
    "delete_observations": {
        "schema": DeleteObservationsRequest,
        "endpoint": "/knowledge/observations/delete",
        "method": "post",
        "description": "Delete observations",
    },
    "delete_relations": {
        "schema": DeleteRelationsRequest,
        "endpoint": "/knowledge/relations/delete",
        "method": "post",
        "description": "Delete relations",
    },
    # Document tools
    "create_document": {
        "schema": DocumentRequest,  # Use our new validator
        "endpoint": "/documents",
        "method": "post",
        "description": "Create a new document",
    },
    "list_documents": {
        "schema": None,  # No validation needed
        "endpoint": "/documents",
        "method": "get",
        "description": "List all documents",
    },
    "get_document": {
        "schema": IdRequest,
        "endpoint": "/documents/{id}",
        "method": "get",
        "description": "Get a document by ID",
    },
    "update_document": {
        "schema": DocumentUpdateRequest,
        "endpoint": "/documents/{id}",
        "method": "put",
        "description": "Update a document by ID",
    },
    "delete_document": {
        "schema": IdRequest,
        "endpoint": "/documents/{id}",
        "method": "delete",
        "description": "Delete a document by ID",
    },
}


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Define the available tools."""
    logger.debug("Listing available tools")
    tools = []
    
    for name, config in TOOLS.items():
        schema = config["schema"].model_json_schema() if config["schema"] else {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
        
        tools.append(
            Tool(
                name=name,
                description=config["description"],
                inputSchema=schema,
            )
        )
    
    return tools


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
                # For GET requests, don't send ID in params
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

        # Get tool configuration
        tool_config = TOOLS.get(name)
        if tool_config is None:
            raise McpError(METHOD_NOT_FOUND, f"Unknown tool: {name}")

        # Validate arguments using schema if one exists
        if tool_config["schema"]:
            try:
                tool_config["schema"].model_validate(arguments)
            except ValidationError as e:
                raise McpError(INVALID_PARAMS, str(e))

        endpoint = tool_config["endpoint"]
        method = tool_config["method"]

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
            
            # All validation errors are INVALID_PARAMS
            if response.status_code == 422:
                raise McpError(INVALID_PARAMS, error_detail)
            # Resource not found is also INVALID_PARAMS
            elif response.status_code == 404 and "not found" in str(error_detail).lower():
                raise McpError(INVALID_PARAMS, error_detail)
            # Other errors are INTERNAL_ERROR
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