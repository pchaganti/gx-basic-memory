"""MCP server implementation for basic-memory."""
from typing import List, Dict, Any, Optional

from mcp.server import Server
from mcp.types import Tool, EmbeddedResource, TextResourceContents, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError
from pydantic.networks import AnyUrl
from pydantic import TypeAdapter, BaseModel

from basic_memory.config import ProjectConfig, create_project_services
from basic_memory.fileio import EntityNotFoundError
from basic_memory.schemas import (
    ObservationIn, RelationIn, EntityIn, ObservationsIn,
    CreateEntitiesResponse, SearchNodesResponse, OpenNodesResponse,
    AddObservationsResponse, CreateRelationsResponse, DeleteEntitiesResponse,
    DeleteObservationsResponse, EntityOut, ObservationOut
)
from basic_memory.services.memory_service import MemoryService


MIME_TYPE = "application/vnd.basic-memory+json"
url_validator = TypeAdapter(AnyUrl)
BASIC_MEMORY_URI = url_validator.validate_python("basic-memory://response")


def create_response(response: BaseModel) -> EmbeddedResource:
    """Create standard MCP response from any response model."""
    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=BASIC_MEMORY_URI,
            mimeType=MIME_TYPE,
            text=response.model_dump_json()
        )
    )


async def handle_create_entities(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle create_entities tool call."""
    # Validate each entity in the input
    entities_data = [EntityIn.model_validate(entity) for entity in args["entities"]]
    
    # Call service with validated data
    entities = await service.create_entities(entities_data)
    
    # Format response
    response = CreateEntitiesResponse(entities=[EntityOut.model_validate(entity) for entity in entities])
    return create_response(response)


async def handle_search_nodes(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle search_nodes tool call."""
    results = await service.search_nodes(args["query"])
    response = SearchNodesResponse(
        matches=[EntityOut.model_validate(entity) for entity in results],
        query=args["query"]
    )
    return create_response(response)


async def handle_open_nodes(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle open_nodes tool call."""
    entities = await service.open_nodes(args["names"])
    response = OpenNodesResponse(entities=[EntityOut.model_validate(entity) for entity in entities])
    return create_response(response)


async def handle_add_observations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle add_observations tool call."""
    # Validate input
    observations_in = ObservationsIn.model_validate(args)
    
    # Call service with validated data
    observations = await service.add_observations(observations_in)
    
    # Format response
    response = AddObservationsResponse(
        entity_id=observations_in.entity_id,
        added_observations=[ObservationOut.model_validate(observation) for observation in observations]
    )
    return create_response(response)


async def handle_create_relations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle create_relations tool call."""
    # Validate each relation in the input
    relations = [RelationIn.model_validate(r) for r in args["relations"]]
    
    # Call service with validated data
    created = await service.create_relations(relations)
    
    response = CreateRelationsResponse(relations=created)
    return create_response(response)


async def handle_delete_entities(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle delete_entities tool call."""
    deleted = await service.delete_entities(args["names"])
    response = DeleteEntitiesResponse(deleted=deleted)
    return create_response(response)


async def handle_delete_observations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle delete_observations tool call."""
    entity, deleted = await service.delete_observations(args["deletions"])
    response = DeleteObservationsResponse(
        entity=entity,
        deleted=deleted
    )
    return create_response(response)


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
        ) -> List[EmbeddedResource]:
            """Handle tool calls by delegating to the memory service."""
            try:
                service = await create_project_services(
                    self.config,
                    memory_service=memory_service
                )

                match name:
                    case "create_entities":
                        return [await handle_create_entities(service, arguments)]
                    case "search_nodes":
                        return [await handle_search_nodes(service, arguments)]
                    case "open_nodes":
                        return [await handle_open_nodes(service, arguments)]
                    case "add_observations":
                        return [await handle_add_observations(service, arguments)]
                    case "create_relations":
                        return [await handle_create_relations(service, arguments)]
                    case "delete_entities":
                        return [await handle_delete_entities(service, arguments)]
                    case "delete_observations":
                        return [await handle_delete_observations(service, arguments)]
                    case _:
                        raise McpError(
                            METHOD_NOT_FOUND,
                            f"Unknown tool: {name}"
                        )
                
            except ValueError as e:
                raise McpError(INVALID_PARAMS, str(e))
            except EntityNotFoundError as e:
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