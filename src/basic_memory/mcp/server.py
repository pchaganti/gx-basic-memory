"""MCP server implementation using FastAPI TestClient."""
import json
import sys
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from httpx import AsyncClient, ASGITransport
from loguru import logger
from mcp import McpError
from mcp.server import Server
from mcp.types import Tool, EmbeddedResource, TextResourceContents, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import TypeAdapter, AnyUrl

from basic_memory.api.app import app as fastapi_app
from basic_memory.schemas import (
    CreateEntityRequest, SearchNodesRequest, OpenNodesRequest,
    AddObservationsRequest, CreateRelationsRequest, DeleteEntityRequest,
    DeleteObservationsRequest
)

# URI constants
url_validator = TypeAdapter(AnyUrl)
BASIC_MEMORY_URI = url_validator.validate_python("basic-memory://response")
MIME_TYPE = "application/vnd.basic-memory+json"


def create_response(data: Dict[str, Any]) -> EmbeddedResource:
    """Create standard MCP response."""
    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=BASIC_MEMORY_URI,
            mimeType=MIME_TYPE,
            text=json.dumps(data),
        )
    )


@asynccontextmanager
async def get_client():
    """Get FastAPI test client."""
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test"
    ) as client:
        logger.info(f"MCP server base_url {client.base_url}")
        yield client


class MemoryServer(Server):
    """MCP server that forwards requests to FastAPI."""

    def __init__(self):
        super().__init__("basic-memory")
        logger.info("running MemoryServer")

        self.register_handlers()

    def register_handlers(self):
        """Register all handlers."""

        @self.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Define the available tools."""
            return [
                Tool(
                    name="create_entities",
                    description="Create multiple new entities",
                    inputSchema=CreateEntityRequest.model_json_schema()
                ),
                Tool(
                    name="search_nodes",
                    description="Search for nodes",
                    inputSchema=SearchNodesRequest.model_json_schema()
                ),
                Tool(
                    name="open_nodes",
                    description="Open specific nodes",
                    inputSchema=OpenNodesRequest.model_json_schema()
                ),
                Tool(
                    name="add_observations",
                    description="Add observations",
                    inputSchema=AddObservationsRequest.model_json_schema()
                ),
                Tool(
                    name="create_relations",
                    description="Create relations",
                    inputSchema=CreateRelationsRequest.model_json_schema()
                ),
                Tool(
                    name="delete_entities",
                    description="Delete entities",
                    inputSchema=DeleteEntityRequest.model_json_schema()
                ),
                Tool(
                    name="delete_observations",
                    description="Delete observations",
                    inputSchema=DeleteObservationsRequest.model_json_schema()
                )
            ]

        @self.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: Dict[str, Any]
        ) -> List[EmbeddedResource]:
            """Forward tool calls to FastAPI endpoints."""
            try:
                logger.info(f"handle_call_tool: {name}, {arguments}")
                
                # Map tools to FastAPI endpoints
                handlers = {
                    "create_entities": lambda c, a: c.post("/knowledge/entities", json=a),
                    "search_nodes": lambda c, a: c.post("/knowledge/search", json=a),
                    "open_nodes": lambda c, a: c.post("/knowledge/nodes", json=a),
                    "add_observations": lambda c, a: c.post("/knowledge/observations", json=a),
                    "create_relations": lambda c, a: c.post("/knowledge/relations", json=a),
                    "delete_entities": lambda c, a: c.delete(f"/knowledge/entities/{a['names'][0]}"),
                    "delete_observations": lambda c, a: c.delete("/knowledge/observations", json=a)
                }

                # Get tool endpoint
                handler = handlers.get(name)
                if handler is None:
                    raise McpError(METHOD_NOT_FOUND, f"Unknown tool: {name}")

                # invoke the client handler function
                async with get_client() as client:

                    logger.debug(f"invoking handler with arguments: {arguments}")
                    response = await handler(client, arguments)

                    # Handle HTTP errors
                    if response.status_code >= 400:
                        error_data = response.json()
                        if response.status_code == 404:
                            raise McpError(METHOD_NOT_FOUND, error_data.get("detail", "Not found"))
                        elif response.status_code == 422:
                            raise McpError(INVALID_PARAMS, error_data.get("detail", "Invalid parameters"))
                        else:
                            raise McpError(INTERNAL_ERROR, error_data.get("detail", "Internal error"))

                    return [create_response(response.json())]
                
            except ValueError as e:
                # Handle validation errors
                raise McpError(INVALID_PARAMS, str(e))
            except Exception as e:
                # Handle unexpected errors
                if isinstance(e, McpError):
                    raise
                raise McpError(INTERNAL_ERROR, str(e))

        self.handle_list_tools = handle_list_tools
        self.handle_call_tool = handle_call_tool

# Create server instance
server = MemoryServer()


def setup_logging():
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()

    # Add file handler
    logger.add(
        "basic-memory-mcp.log",
        rotation="100 MB",
        level="DEBUG",
        backtrace=True,
        diagnose=True
    )

    # Add stdout handler for INFO and above
    logger.add(
        sys.stdout,
        level="DEBUG",
        backtrace=True,
        diagnose=True
    )


if __name__ == "__main__":
    import asyncio
    setup_logging()
    from mcp.server.stdio import stdio_server

    async def run_server():
        """Run the MCP server."""
        options = server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options)

    asyncio.run(run_server())