"""Search and query tools for Basic Memory MCP server."""
from typing import Dict

from basic_memory.schemas.request import SearchNodesRequest, OpenNodesRequest
from basic_memory.schemas.response import SearchNodesResponse, EntityResponse
from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp


@mcp.tool()
async def search_nodes(request: SearchNodesRequest) -> SearchNodesResponse:
    """Search for entities in the knowledge graph.
    
    Examples:
        # Find technical implementation details
        request = SearchNodesRequest(
            query="SQLite implementation",
            category=ObservationCategory.TECH
        )
        response = await search_nodes(request)
        
        # Response contains matching entities:
        # SearchNodesResponse(
        #     matches=[
        #         EntityResponse(  # First matching entity
        #             path_id="component/memory_service",
        #             name="memory_service",
        #             description="Core service for persistence",
        #             observations=[
        #                 Observation(
        #                     category="TECH",
        #                     content="Using SQLite for storage"
        #                 )
        #             ]
        #         ),
        #         EntityResponse(...)  # Other matches
        #     ],
        #     query="SQLite implementation"
        # )

        # Find design decisions
        request = SearchNodesRequest(
            query="database design decision",
            category=ObservationCategory.DESIGN
        )
        response = await search_nodes(request)
    """
    url = "/knowledge/search"
    response = await client.post(url, json=request.model_dump())
    return SearchNodesResponse.model_validate(response.json())


@mcp.tool()
async def open_nodes(request: OpenNodesRequest) -> Dict[str, EntityResponse]:
    """Load multiple entities by their path_ids.
    
    Examples:
        # Load related components and their specs
        request = OpenNodesRequest(
            path_ids=[
                "component/memory_service",
                "component/file_service",
                "specification/file_format"
            ]
        )
        response = await open_nodes(request)
        
        # Response maps path_ids to entities:
        # {
        #     "component/memory_service": EntityResponse(...),
        #     "component/file_service": EntityResponse(...),
        #     "specification/file_format": EntityResponse(...)
        # }
        
        # Follow relation chains
        request = OpenNodesRequest(
            path_ids=[
                "feature/search",  # The feature
                "component/search_service",  # Implementation
                "test/search_integration"  # Testing
            ]
        )
        response = await open_nodes(request)
    """
    url = "/knowledge/nodes"
    response = await client.post(url, json=request.model_dump())
    return {entity["path_id"]: EntityResponse.model_validate(entity) 
            for entity in response.json()["entities"]}