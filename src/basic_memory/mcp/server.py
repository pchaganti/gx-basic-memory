"""MCP server implementation for basic-memory."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncEngine
from typing_extensions import TypeAlias

from mcp.server import Server
from mcp.types import Tool, EmbeddedResource, TextResourceContents, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError
from pydantic.networks import AnyUrl
from pydantic import TypeAdapter, BaseModel

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.fileio import EntityNotFoundError
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.observation_repository import ObservationRepository
from basic_memory.repository.relation_repository import RelationRepository
from basic_memory.schemas import (
    # Tool inputs
    CreateEntityRequest, SearchNodesRequest, OpenNodesRequest,
    CreateRelationsRequest, DeleteEntityRequest,
    DeleteObservationsRequest,
    # Tool responses
    CreateEntityResponse, SearchNodesResponse, OpenNodesResponse,
    AddObservationsResponse, CreateRelationsResponse, DeleteEntityResponse,
    EntityResponse, ObservationResponse, RelationResponse, AddObservationsRequest
)
from basic_memory.services import EntityService, ObservationService, RelationService
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

@asynccontextmanager
async def get_memory_service_session(engine: AsyncEngine, project_path: Path):
    """Get all services with proper session and lifecycle management."""
    async with db.session(engine) as session:
        # Create repos
        entity_repo = EntityRepository(session)
        observation_repo = ObservationRepository(session)
        relation_repo = RelationRepository(session)

        # Create services
        entity_service = EntityService(project_path, entity_repo)
        observation_service = ObservationService(project_path, observation_repo)
        relation_service = RelationService(project_path, relation_repo)

        # Create memory service
        memory_service = MemoryService(
            project_path=project_path,
            entity_service=entity_service,
            relation_service=relation_service,
            observation_service=observation_service
        )

        yield memory_service

@asynccontextmanager
async def get_project_services(project_path: Path):
    """Get all services for a project with full lifecycle management."""
    async with db.engine(project_path=project_path) as engine:
        async with get_memory_service_session(engine, project_path) as services:
            yield services

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
    input_args = CreateEntityRequest.model_validate(args)
    logger.debug(f"Validated input: {len(input_args.entities)} entities")
    
    # Call service with validated data
    entities = await service.create_entities(input_args.entities)
    logger.debug(f"Created {len(entities)} entities")
    
    # Format response
    response = CreateEntityResponse(entities=[EntityResponse.model_validate(entity) for entity in entities])
    logger.debug("Formatted create_entities response")
    return create_response(response)


async def handle_search_nodes(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle search_nodes tool call."""
    logger.debug(f"Searching nodes with query: {args.get('query')}")
    input_args = SearchNodesRequest.model_validate(args)
    results = await service.search_nodes(input_args.query)
    logger.debug(f"Found {len(results)} matches for query '{input_args.query}'")
    response = SearchNodesResponse(
        matches=[EntityResponse.model_validate(entity) for entity in results],
        query=input_args.query
    )
    return create_response(response)


async def handle_open_nodes(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle open_nodes tool call."""
    logger.debug(f"Opening nodes: {args.get('names')}")
    input_args = OpenNodesRequest.model_validate(args)
    entities = await service.open_nodes(input_args.names)
    logger.debug(f"Opened {len(entities)} entities")
    response = OpenNodesResponse(entities=[EntityResponse.model_validate(entity) for entity in entities])
    return create_response(response)


async def handle_add_observations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle add_observations tool call."""
    # Validate input
    logger.debug(f"Adding observations: {args}")
    input_args = AddObservationsRequest.model_validate(args)
    logger.debug(f"Adding {len(input_args.observations)} observations to entity {input_args.entity_id}")

    # Call service with validated data
    observations = await service.add_observations(input_args)
    logger.debug(f"Added {len(observations)} observations")
    
    # Format response
    response = AddObservationsResponse(
        entity_id=input_args.entity_id,
        observations=[ObservationResponse.model_validate(obs) for obs in observations]
    )
    return create_response(response)


async def handle_create_relations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle create_relations tool call."""
    # Validate input
    logger.debug(f"Creating relations: {args}")
    input_args = CreateRelationsRequest.model_validate(args)
    logger.debug(f"Creating {len(input_args.relations)} relations")
    
    # Call service with validated data
    created = await service.create_relations(input_args.relations)
    logger.debug(f"Created {len(created)} relations")
    
    # Format response
    response = CreateRelationsResponse(relations=[RelationResponse.model_validate(relation) for relation in created])
    return create_response(response)


async def handle_delete_entities(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle delete_entities tool call."""
    logger.debug(f"Deleting entities: {args}")
    input_args = DeleteEntityRequest.model_validate(args)
    deleted = await service.delete_entities(input_args.names)
    logger.debug(f"Deleted entities: {deleted}")
    response = DeleteEntityResponse(deleted=deleted)
    return create_response(response)


async def handle_delete_observations(
    service: MemoryService, 
    args: Dict[str, Any]
) -> EmbeddedResource:
    """Handle delete_observations tool call."""
    logger.debug(f"Deleting observations: {args}")
    return EmbeddedResource()


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
                    inputSchema=CreateEntityRequest.model_json_schema()
                ),
                Tool(
                    name="search_nodes", 
                    description="Search for nodes in the knowledge graph",
                    inputSchema=SearchNodesRequest.model_json_schema()
                ),
                Tool(
                    name="open_nodes",
                    description="Open specific nodes by their names",
                    inputSchema=OpenNodesRequest.model_json_schema()
                ),
                Tool(
                    name="add_observations",
                    description="Add observations to existing entities",
                    inputSchema=AddObservationsRequest.model_json_schema()
                ),
                Tool(
                    name="create_relations",
                    description="Create relations between entities",
                    inputSchema=CreateRelationsRequest.model_json_schema()
                ),
                Tool(
                    name="delete_entities",
                    description="Delete entities from the knowledge graph",
                    inputSchema=DeleteEntityRequest.model_json_schema()
                ),
                Tool(
                    name="delete_observations",
                    description="Delete observations from entities",
                    inputSchema=DeleteObservationsRequest.model_json_schema()
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