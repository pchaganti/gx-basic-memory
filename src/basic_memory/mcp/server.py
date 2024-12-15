"""Basic Memory MCP server implementation.

Creates a server that handles MCP tool calls and forwards them to our FastAPI endpoints.
Uses proper lifecycle management and logging to ensure reliable operation.
"""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

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
    """Create standard MCP response wrapper."""
    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=BASIC_MEMORY_URI,
            mimeType=MIME_TYPE,
            text=json.dumps(data),
        )
    )


class MemoryServer(Server):
    """MCP server that forwards requests to FastAPI endpoints.
    
    Handles proper lifecycle management and maintains a single client connection.
    """

    def __init__(self):
        """Initialize the server with 'basic-memory' namespace."""
        super().__init__("basic-memory")
        self.client: Optional[AsyncClient] = None
        self.ready = False
        logger.info("Initializing MemoryServer")
        self.register_handlers()

    async def setup(self):
        """Initialize server resources and API client."""
        logger.info("Setting up MemoryServer resources")
        self.client = AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://test",
            timeout=30.0  # 30 second timeout
        )
        await self.client.__aenter__()
        self.ready = True
        logger.info("MemoryServer setup complete")

    async def cleanup(self):
        """Clean up server resources properly."""
        logger.info("Cleaning up MemoryServer")
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error during client cleanup: {e}")
            finally:
                self.client = None
        self.ready = False
        logger.info("MemoryServer cleanup complete")

    def register_handlers(self):
        """Register all tool handlers."""

        @self.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Define the available tools."""
            logger.debug("Listing available tools")
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
            # Check server is ready
            if not self.ready or not self.client:
                raise McpError(INTERNAL_ERROR, "Server not initialized")

            try:
                logger.info(f"Tool call: {name}")
                logger.debug(f"Arguments: {arguments}")
                
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

                # Get handler for tool
                handler = handlers.get(name)
                if handler is None:
                    raise McpError(METHOD_NOT_FOUND, f"Unknown tool: {name}")

                # Make API call
                logger.debug(f"Calling API endpoint for {name}")
                response = await handler(self.client, arguments)

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

        # Store handlers
        self.handle_list_tools = handle_list_tools
        self.handle_call_tool = handle_call_tool


def setup_logging(log_file: str = "basic-memory-mcp.log"):
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()

    # Add file handler with rotation
    logger.add(
        log_file,
        rotation="100 MB",
        retention="10 days",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Add stdout handler for INFO and above
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <white>{message}</white>",
        colorize=True
    )


# Create server instance
server = MemoryServer()


if __name__ == "__main__":
    from mcp.server.stdio import stdio_server

    async def run_server():
        """Run the MCP server with proper initialization and cleanup."""
        setup_logging()
        logger.info("Starting Basic Memory MCP server")
        
        try:
            # Initialize server
            options = server.create_initialization_options()
            logger.debug(f"Server initialization options: {options}")
            await server.setup()
            
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
            await server.cleanup()

    # Run with proper asyncio error handling
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {e}")
        sys.exit(1)