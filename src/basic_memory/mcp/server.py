"""MCP server implementation for basic-memory."""
import sys
import os
from typing import List, Dict, Any, Optional, Literal, Callable, Awaitable
from typing_extensions import TypeAlias

from mcp.server import Server
from mcp.types import Tool, EmbeddedResource, TextResourceContents, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError
from pydantic.networks import AnyUrl
from pydantic import TypeAdapter, BaseModel, ConfigDict

from basic_memory.config import ProjectConfig
from basic_memory.deps import get_project_services
from basic_memory.fileio import EntityNotFoundError
from basic_memory.schemas import (
    # Tool inputs
    CreateEntitiesInput, SearchNodesInput, OpenNodesInput,
    AddObservationsInput, CreateRelationsInput, DeleteEntitiesInput,
    DeleteObservationsInput,
    # Tool responses
    CreateEntitiesResponse, SearchNodesResponse, OpenNodesResponse,
    AddObservationsResponse, CreateRelationsResponse, DeleteEntitiesResponse,
    DeleteObservationsResponse,
    # Base models
    EntityOut, ObservationOut, RelationOut
)
from basic_memory.services.memory_service import MemoryService
from loguru import logger

MIME_TYPE = "application/vnd.basic-memory+json"
url_validator = TypeAdapter(AnyUrl)
BASIC_MEMORY_URI = url_validator.validate_python("basic-memory://response")

# Define tool name type and handler type
ToolName = Literal[
    "create_entities",
    "search_nodes",
    "open_nodes",
    "add_observations",
    "create_relations",
    "delete_entities",
    "delete_observations"
]

ToolHandler: TypeAlias = Callable[[MemoryService, Dict[str, Any]], Awaitable[EmbeddedResource]]


def create_response(response: BaseModel) -> EmbeddedResource:
    """Create standard MCP response from any response model."""
    logger.debug(f"Creating MCP response from {response.__class__.__name__}")
    result = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=BASIC_MEMORY_URI,
            mimeType=MIME_TYPE,
            text=response.model_dump_json()
        )
    )
    logger.debug(f"Created response: {result}")
    return result


async def handle_create_entities(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle create_entities tool call."""
    # Validate input
    logger.debug(f"Creating entities with args: {args}")
    input_args = CreateEntitiesInput.model_validate(args)
    logger.debug(f"Validated input: {len(input_args.entities)} entities")
    
    # Call service with validated data
    entities = await service.create_entities(input_args.entities)
    logger.debug(f"Created {len(entities)} entities")
    
    # Format response
    response = CreateEntitiesResponse(entities=[EntityOut.model_validate(entity) for entity in entities])
    logger.debug("Formatted create_entities response")
    return create_response(response)


async def handle_search_nodes(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle search_nodes tool call."""
    logger.debug(f"Searching nodes with query: {args.get('query')}")
    input_args = SearchNodesInput.model_validate(args)
    results = await service.search_nodes(input_args.query)
    logger.debug(f"Found {len(results)} matches for query '{input_args.query}'")
    response = SearchNodesResponse(
        matches=[EntityOut.model_validate(entity) for entity in results],
        query=input_args.query
    )
    return create_response(response)


async def handle_open_nodes(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle open_nodes tool call."""
    logger.debug(f"Opening nodes: {args.get('names')}")
    input_args = OpenNodesInput.model_validate(args)
    entities = await service.open_nodes(input_args.names)
    logger.debug(f"Opened {len(entities)} entities")
    response = OpenNodesResponse(entities=[EntityOut.model_validate(entity) for entity in entities])
    return create_response(response)


async def handle_add_observations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle add_observations tool call."""
    # Validate input
    logger.debug(f"Adding observations: {args}")
    input_args = AddObservationsInput.model_validate(args)
    logger.debug(f"Adding {len(input_args.observations)} observations to entity {input_args.entity_id}")
    
    # Call service with validated data
    observations = await service.add_observations(input_args)
    logger.debug(f"Added {len(observations)} observations")
    
    # Format response
    response = AddObservationsResponse(
        entity_id=input_args.entity_id,
        added_observations=[ObservationOut.model_validate(obs) for obs in observations]
    )
    return create_response(response)


async def handle_create_relations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle create_relations tool call."""
    # Validate input
    logger.debug(f"Creating relations: {args}")
    input_args = CreateRelationsInput.model_validate(args)
    logger.debug(f"Creating {len(input_args.relations)} relations")
    
    # Call service with validated data
    created = await service.create_relations(input_args.relations)
    logger.debug(f"Created {len(created)} relations")
    
    # Format response
    response = CreateRelationsResponse(relations=[RelationOut.model_validate(relation) for relation in created])
    return create_response(response)


async def handle_delete_entities(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle delete_entities tool call."""
    logger.debug(f"Deleting entities: {args}")
    input_args = DeleteEntitiesInput.model_validate(args)
    deleted = await service.delete_entities(input_args.names)
    logger.debug(f"Deleted entities: {deleted}")
    response = DeleteEntitiesResponse(deleted=deleted)
    return create_response(response)


async def handle_delete_observations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle delete_observations tool call."""
    logger.debug(f"Deleting observations: {args}")
    input_args = DeleteObservationsInput.model_validate(args)
    entity, deleted = await service.delete_observations(input_args.deletions)
    logger.debug(f"Deleted {len(deleted)} observations from entity {entity}")
    response = DeleteObservationsResponse(
        entity=entity,
        deleted=deleted
    )
    return create_response(response)


# Map tool names to handlers
TOOL_HANDLERS: Dict[ToolName, ToolHandler] = {
    "create_entities": handle_create_entities,
    "search_nodes": handle_search_nodes,
    "open_nodes": handle_open_nodes,
    "add_observations": handle_add_observations,
    "create_relations": handle_create_relations,
    "delete_entities": handle_delete_entities,
    "delete_observations": handle_delete_observations,
}


class MemoryServer(Server):
    """Extended server class that exposes handlers for testing."""
    
    def __init__(self, config: Optional[ProjectConfig] = None):
        super().__init__("basic-memory")
        self.config = config or ProjectConfig()
        logger.debug(f"Initialized MemoryServer with config: {self.config}")
        self.register_handlers()
    
    def register_handlers(self):
        """Register all handlers with proper decorators."""
        
        @self.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Define the available tools."""
            logger.debug("Listing available tools")
            tools = [
                Tool(
                    name="create_entities",
                    description="Create multiple new entities in the knowledge graph",
                    inputSchema=CreateEntitiesInput.model_json_schema()
                ),
                Tool(
                    name="search_nodes", 
                    description="Search for nodes in the knowledge graph",
                    inputSchema=SearchNodesInput.model_json_schema()
                ),
                Tool(
                    name="open_nodes",
                    description="Open specific nodes by their names",
                    inputSchema=OpenNodesInput.model_json_schema()
                ),
                Tool(
                    name="add_observations",
                    description="Add observations to existing entities",
                    inputSchema=AddObservationsInput.model_json_schema()
                ),
                Tool(
                    name="create_relations",
                    description="Create relations between entities",
                    inputSchema=CreateRelationsInput.model_json_schema()
                ),
                Tool(
                    name="delete_entities",
                    description="Delete entities from the knowledge graph",
                    inputSchema=DeleteEntitiesInput.model_json_schema()
                ),
                Tool(
                    name="delete_observations",
                    description="Delete observations from entities",
                    inputSchema=DeleteObservationsInput.model_json_schema()
                )
            ]
            logger.debug(f"Returning {len(tools)} available tools")
            return tools
        
        @self.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any],
            *,
            memory_service: Optional[MemoryService] = None
        ) -> List[EmbeddedResource]:
            """Handle tool calls by delegating to the memory service."""
            try:
                logger.debug(f"Handling tool call: {name} with args: {arguments}")
                # Check if tool exists
                if name not in TOOL_HANDLERS:
                    logger.error(f"Unknown tool requested: {name}")
                    raise McpError(METHOD_NOT_FOUND, f"Unknown tool: {name}")

                async with get_project_services(self.config.path) as service:
                    tool_name = name  # type: ignore
                    result = [await TOOL_HANDLERS[tool_name](service, arguments)]
                    logger.debug(f"Tool {name} completed successfully")
                    return result
                
            except ValueError as e:
                logger.error(f"Invalid parameters for {name}: {e}")
                raise McpError(INVALID_PARAMS, str(e))
            except EntityNotFoundError as e:
                logger.error(f"Entity not found in {name}: {e}")
                raise McpError(INVALID_PARAMS, str(e))
            except Exception as e:
                logger.exception(f"Unexpected error in {name}: {e}")
                raise McpError(INTERNAL_ERROR, str(e))
        
        # Store handlers as instance attributes for testing
        self.handle_list_tools = handle_list_tools
        self.handle_call_tool = handle_call_tool
        logger.debug("Registered all handlers")


# Create server instance with default config
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
        level="INFO",
        backtrace=True,
        diagnose=True
    )

async def run_server():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    options = server.create_initialization_options()
    logger.info(f"Starting MCP server {options.server_name}")
    logger.info(f"Database URL: {server.config.database_url}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    setup_logging()
    import asyncio
    asyncio.run(run_server())