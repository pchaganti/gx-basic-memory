"""MCP server implementation for basic-memory."""
from pathlib import Path
from typing import List, Dict, Any

from mcp.server import Server
from mcp.types import Tool, TextContent, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError

from basic_memory import deps
from basic_memory.schemas import EntityIn, ObservationIn, RelationIn

class MemoryServer(Server):
    """Extended server class that exposes handlers for testing."""
    
    def __init__(self):
        super().__init__("basic-memory")
        self.register_handlers()
    
    def register_handlers(self):
        """Register all handlers with proper decorators."""
        
        @self.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Define the available tools."""
            return [
                Tool(
                    name="create_entities",
                    description="Create multiple new entities in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": EntityIn.model_json_schema(),
                                "minItems": 1
                            }
                        },
                        "required": ["entities"]
                    }
                ),
                Tool(
                    name="search_nodes", 
                    description="Search for nodes in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "minLength": 1
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="open_nodes",
                    description="Open specific nodes by their names",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1
                            }
                        },
                        "required": ["names"]
                    }
                ),
                Tool(
                    name="add_observations",
                    description="Add observations to existing entities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entityId": {"type": "string"},
                            "observations": {
                                "type": "array",
                                "items": ObservationIn.model_json_schema(),
                                "minItems": 1
                            }
                        },
                        "required": ["entityId", "observations"]
                    }
                ),
                Tool(
                    name="create_relations",
                    description="Create relations between entities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "relations": {
                                "type": "array",
                                "items": RelationIn.model_json_schema(),
                                "minItems": 1
                            }
                        },
                        "required": ["relations"]
                    }
                ),
                Tool(
                    name="delete_entities",
                    description="Delete entities from the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1
                            }
                        },
                        "required": ["names"]
                    }
                ),
                Tool(
                    name="delete_observations",
                    description="Delete observations from entities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "deletions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "entityName": {"type": "string"},
                                        "observations": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "minItems": 1
                                        }
                                    },
                                    "required": ["entityName", "observations"]
                                }
                            }
                        },
                        "required": ["deletions"]
                    }
                )
            ]
        
        @self.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls by delegating to the memory service."""
            try:
                # Get project path (could come from context in future)
                project_path = Path.home() / ".basic-memory" / "projects" / "default"

                # Get services with proper lifecycle management
                async with deps.get_project_services(project_path) as memory_service:
                    match name:
                        case "create_entities":
                            # Each entity in arguments["entities"] will be validated by EntityIn
                            result = await memory_service.create_entities(arguments["entities"])
                            return [TextContent(type="text", text=str(result))]
                        
                        case "search_nodes":
                            result = await memory_service.search_nodes(arguments["query"])
                            return [TextContent(type="text", text=str(result))]
                            
                        case "open_nodes":
                            result = await memory_service.open_nodes(arguments["names"])
                            return [TextContent(type="text", text=str(result))]
                            
                        case "add_observations":
                            result = await memory_service.add_observations(arguments)
                            return [TextContent(type="text", text=str(result))]
                            
                        case "create_relations":
                            result = await memory_service.create_relations(arguments["relations"])
                            return [TextContent(type="text", text=str(result))]
                            
                        case "delete_entities":
                            await memory_service.delete_entities(arguments["names"])
                            return [TextContent(type="text", text="Entities deleted")]
                            
                        case "delete_observations":
                            await memory_service.delete_observations(arguments["deletions"])
                            return [TextContent(type="text", text="Observations deleted")]
                        
                        case _:
                            raise McpError(
                                METHOD_NOT_FOUND,
                                f"Unknown tool: {name}"
                            )
                    
            except ValueError as e:
                raise McpError(INVALID_PARAMS, str(e))
            except Exception as e:
                raise McpError(INTERNAL_ERROR, str(e))
        
        # Store handlers as instance attributes for testing
        self.handle_list_tools = handle_list_tools
        self.handle_call_tool = handle_call_tool

# Create server instance
server = MemoryServer()

async def run_server():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server())