"""MCP server implementation using FastAPI TestClient."""
import json
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from httpx import AsyncClient, ASGITransport
from mcp import McpError
from mcp.server import Server
from mcp.types import Tool, EmbeddedResource, TextResourceContents
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
        yield client


class MemoryServer(Server):
    """MCP server that forwards requests to FastAPI."""

    def __init__(self):
        super().__init__("basic-memory")
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
                raise McpError(f"Unknown tool {name}")

            # invoke the client handler function
            async with get_client() as client:
                response = await handler(client, arguments)
                return [create_response(response.json())]


        self.handle_list_tools = handle_list_tools
        self.handle_call_tool = handle_call_tool

# Create server instance
server = MemoryServer()

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def run_server():
        """Run the MCP server."""
        options = server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options)

    asyncio.run(run_server())