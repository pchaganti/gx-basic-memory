"""MCP server implementation for basic-memory."""
from pathlib import Path
from typing import Annotated, List, Dict, Any

from mcp.server import Server
from mcp.types import Tool, TextContent, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError
from pydantic import BaseModel, Field

from basic_memory import deps

# Create server instance
server = Server("basic-memory")

# Parameter models
class CreateEntitiesParams(BaseModel):
    """Parameters for creating entities."""
    entities: Annotated[List[Dict[str, Any]], Field(
        description="List of entities to create",
        min_items=1
    )]

class SearchNodesParams(BaseModel):
    """Parameters for searching nodes."""
    query: Annotated[str, Field(
        description="Search query to match against entities"
    )]

@server.list_tools()
async def list_tools() -> List[Tool]:
    """Define the available tools."""
    return [
        Tool(
            name="create_entities",
            description="Create multiple new entities in the knowledge graph",
            inputSchema=CreateEntitiesParams.model_json_schema()
        ),
        Tool(
            name="search_nodes",
            description="Search for nodes in the knowledge graph",
            inputSchema=SearchNodesParams.model_json_schema()
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls by delegating to the memory service."""
    try:
        # Get project path (could come from context in future)
        project_path = Path.home() / ".basic-memory" / "projects" / "default"

        # Get services with proper lifecycle management
        async with deps.get_project_services(project_path) as memory_service:
            match name:
                case "create_entities":
                    params = CreateEntitiesParams(**arguments)
                    result = await memory_service.create_entities(params.entities)
                    return [TextContent(type="text", text=str(result))]
                
                case "search_nodes":
                    params = SearchNodesParams(**arguments)
                    result = await memory_service.search_nodes(params.query)
                    return [TextContent(type="text", text=str(result))]
                
                case _:
                    raise McpError(
                        METHOD_NOT_FOUND,
                        f"Unknown tool: {name}"
                    )
                    
    except ValueError as e:
        raise McpError(INVALID_PARAMS, str(e))
    except Exception as e:
        raise McpError(INTERNAL_ERROR, str(e))

async def run_server():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server())