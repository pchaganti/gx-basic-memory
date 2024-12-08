"""MCP server implementation for basic-memory."""
from typing import List, Dict, Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError

from basic_memory.config import ProjectConfig, create_project_services
from basic_memory.schemas import ObservationIn, RelationIn, EntityIn
from basic_memory.services.memory_service import MemoryService

class MemoryServer(Server):
    """Extended server class that exposes handlers for testing."""
    
    def __init__(self, config: Optional[ProjectConfig] = None):
        super().__init__("basic-memory")
        self.config = config or ProjectConfig()
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
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any],
            *,
            memory_service: Optional[MemoryService] = None
        ) -> List[TextContent]:
            """Handle tool calls by delegating to the memory service."""
            try:
                service = await create_project_services(
                    self.config,
                    memory_service=memory_service
                )

                match name:
                    case "create_entities":
                        # Each entity in arguments["entities"] will be validated by EntityIn
                        result = await service.create_entities(arguments["entities"])
                        return [TextContent(type="text", text=str(result))]
                    
                    case "search_nodes":
                        result = await service.search_nodes(arguments["query"])
                        return [TextContent(type="text", text=str(result))]
                        
                    case "open_nodes":
                        result = await service.open_nodes(arguments["names"])
                        return [TextContent(type="text", text=str(result))]
                        
                    case "add_observations":
                        result = await service.add_observations(arguments)
                        return [TextContent(type="text", text=str(result))]
                        
                    case "create_relations":
                        result = await service.create_relations(arguments["relations"])
                        return [TextContent(type="text", text=str(result))]
                        
                    case "delete_entities":
                        await service.delete_entities(arguments["names"])
                        return [TextContent(type="text", text="Entities deleted")]
                        
                    case "delete_observations":
                        await service.delete_observations(arguments["deletions"])
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

# Create server instance with default config
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