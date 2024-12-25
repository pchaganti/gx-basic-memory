"""Basic Memory MCP server using fastmcp - proxies to FastAPI endpoints."""

import sys
from typing import Any, List

from fastmcp import FastMCP
from loguru import logger

from basic_memory.mcp.async_client import client

# Create FastMCP server
mcp = FastMCP("Basic Memory")


def setup_logging(log_file: str = "basic-memory-mcp.log"):
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()

    # Add file handler with rotation (no colors)
    logger.add(
        log_file,
        rotation="100 MB",
        retention="10 days",
        # level="DEBUG",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
        # format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        colorize=False,
    )

    # Add stderr handler
    logger.add(
        sys.stderr,
        # level="INFO",
        # format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <white>{message}</white>",
        colorize=True,
    )


async def log_api_call(method: str, url: str, data: Any, response: Any):
    """Log API request and response details."""
    logger.debug(f"API Request: {method} {url}")
    logger.debug(f"Request Data: {data}")
    logger.debug(f"Response Status: {response.status_code}")
    if response.status_code != 204:  # Only try to log response data if it's not No Content
        logger.debug(f"Response Data: {response.json()}")


# Knowledge Graph Tools

## Create endpoints


@mcp.tool()
async def create_entities(entities: list[dict]) -> dict:
    """Create new entities in the knowledge graph."""
    url = "/knowledge/entities"
    data = {"entities": entities}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def create_relations(relations: list[dict]) -> dict:
    """Create relations between entities."""
    url = "/knowledge/relations"
    data = {"relations": relations}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def add_observations(path_id: str, observations: list[str]) -> dict:
    """Add observations to an entity."""
    url = "/knowledge/observations"
    data = {"path_id": path_id, "observations": observations}
    response = await client.post(url, json=data)
    await log_api_call("POST", url, data, response)
    return response.json()


## Read endpoints


@mcp.tool()
async def get_entity(path_id: str) -> dict:
    """Get a specific entity by path_id."""
    url = f"/knowledge/entities/{path_id}"
    response = await client.get(url)
    return response.json()


@mcp.tool()
async def search_nodes(query: str) -> dict:
    """Search for entities in the knowledge graph."""
    url = "/knowledge/search"
    data = {"query": query}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def open_nodes(path_ids: List[str]) -> dict:
    """Search for entities in the knowledge graph."""
    url = "/knowledge/nodes"
    data = {"path_ids": path_ids}
    response = await client.post(url, json=data)
    return response.json()


## Delete endpoints


@mcp.tool()
async def delete_entities(path_ids: List[str]) -> dict:
    """Search for entities in the knowledge graph."""
    url = "/knowledge/entities/delete"
    data = {"path_ids": path_ids}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def delete_observations(path_id: str, observations: list[str]) -> dict:
    """Delete observations from an entity."""
    url = "/knowledge/observations/delete"
    data = {
        "path_id": path_id,
        "observations": observations,
    }
    response = await client.post(
        url, json=data
    )  
    return response.json()


@mcp.tool()
async def delete_relations(relations: list[dict]) -> dict:
    """Delete relations between entities."""
    url = "/knowledge/relations/delete"
    data = {"relations": relations}
    response = await client.post(
        url, json=data
    ) 
    return response.json()


# Document Tools


@mcp.tool()
async def create_document(path: str, content: str, metadata: dict = None) -> dict:
    """Create a new document."""
    url = "/documents/create"
    data = {"path": path, "content": content, "metadata": metadata}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def get_document(path: str) -> dict:
    """Get a document by path_id."""
    url = f"/documents/{path}"
    response = await client.get(url)
    return response.json()


@mcp.tool()
async def update_document(path: str, content: str, metadata: dict = None) -> dict:
    """Update an existing document."""
    url = f"/documents/{path}"
    data = {"path": path, "content": content, "metadata": metadata}
    response = await client.put(url, json=data)
    return response.json()


@mcp.tool()
async def list_documents() -> list:
    """List all documents."""
    url = "/documents/list"
    response = await client.get(url)
    return response.json()


@mcp.tool()
async def delete_document(path: str) -> dict:
    """Delete an existing document."""
    url = f"/documents/{path}"
    response = await client.delete(url)
    if response.status_code == 204:
        return {"deleted": True}


if __name__ == "__main__":
    setup_logging()
    logger.info("Starting Basic Memory MCP server")
    mcp.run()
