"""Basic Memory MCP server using fastmcp - proxies to FastAPI endpoints."""

import sys
from typing import Any, List

from fastmcp import FastMCP
from httpx import AsyncClient, ASGITransport
from loguru import logger

from basic_memory.api.app import app as fastapi_app

# Create FastMCP server
mcp = FastMCP("Basic Memory")

# Create shared async client
client = AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")

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
    logger.debug(f"Response Data: {response.json()}")

# Knowledge Graph Tools

## Create endpoints

@mcp.tool()
async def create_entities(entities: list[dict]) -> dict:
    """Create new entities in the knowledge graph."""
    response = await client.post("/knowledge/entities", json={"entities": entities})
    await log_api_call("POST", "/knowledge/entities", entities, response)
    return response.json()

@mcp.tool()
async def create_relations(relations: list[dict]) -> dict:
    """Create relations between entities."""
    response = await client.post("/knowledge/relations", json={"relations": relations})
    await log_api_call("POST", "/knowledge/relations", relations, response)
    return response.json()

@mcp.tool()
async def add_observations(path_id: str, observations: list[str]) -> dict:
    """Add observations to an entity."""
    data = {"path_id": path_id, "observations": observations}
    response = await client.post("/knowledge/observations", json=data)
    await log_api_call("POST", "/knowledge/observations", data, response)
    return response.json()

## Read endpoints

@mcp.tool()
async def get_entity(path_id: str) -> dict:
    """Get a specific entity by path_id."""
    response = await client.get(f"/knowledge/entities/{path_id}")
    await log_api_call("GET", f"/knowledge/entities/{path_id}", None, response)
    return response.json()


@mcp.tool()
async def search_nodes(query: str) -> dict:
    """Search for entities in the knowledge graph."""
    response = await client.post("/knowledge/search", json={"query": query})
    await log_api_call("POST", "/knowledge/search", {"query": query}, response)
    return response.json()

@mcp.tool()
async def open_nodes(path_ids: List[str]) -> dict:
    """Search for entities in the knowledge graph."""
    response = await client.post("/knowledge/nodes", json={"path_ids": path_ids})
    await log_api_call("POST", "/knowledge/nodes", {"path_ids": path_ids}, response)
    return response.json()

## Delete endpoints

@mcp.tool()
async def delete_entities(path_ids: List[str]) -> dict:
    """Search for entities in the knowledge graph."""
    response = await client.post("/knowledge/entities/delete", json={"path_ids": path_ids})
    await log_api_call("POST", "/knowledge/entities/delete", {"path_ids": path_ids}, response)
    return response.json()

@mcp.tool()
async def delete_observations(path_id: str, observations: list[str]) -> dict:
    """Delete observations from an entity."""
    data = {"path_id": path_id, "observations": observations}  # Match the parameter name with what we're using
    response = await client.post("/knowledge/observations/delete", json=data)  # Change to observations endpoint
    await log_api_call("POST", "/knowledge/observations/delete", data, response)
    return response.json()

@mcp.tool()
async def delete_relations(relations: list[dict]) -> dict:
    """Delete relations between entities."""
    response = await client.post("/knowledge/relations/delete", json={"relations": relations})  # Change to relations endpoint
    await log_api_call("POST", "/knowledge/relations/delete", {"relations": relations}, response)
    return response.json()


# Document Tools


@mcp.tool()
async def create_document(path: str, content: str, metadata: dict = None) -> dict:
    """Create a new document."""
    data = {"path": path, "content": content, "metadata": metadata}
    response = await client.post("/documents", json=data)
    await log_api_call("POST", "/documents", data, response)
    return response.json()

@mcp.tool()
async def get_document(path_id: str) -> dict:
    """Get a document by path_id."""
    response = await client.get(f"/documents/{path_id}")
    await log_api_call("GET", f"/documents/{path_id}", None, response)
    return response.json()

@mcp.tool()
async def update_document(path_id: str, content: str, metadata: dict = None) -> dict:
    """Update an existing document."""
    data = {"path": path_id, "content": content, "metadata": metadata}
    response = await client.put(f"/documents/{path_id}", json=data)
    await log_api_call("PUT", f"/documents/{path_id}", data, response)
    return response.json()

@mcp.tool()
async def list_documents() -> list:
    """List all documents."""
    response = await client.get("/documents")
    await log_api_call("GET", "/documents", None, response)
    return response.json()

@mcp.tool()
async def delete_document(path_id: str) -> dict:
    """Update an existing document."""
    response = await client.put(f"/documents/{path_id}")
    await log_api_call("DELETE", f"/documents/{path_id}", None, response)
    return response.json()

if __name__ == "__main__":
    setup_logging()
    logger.info("Starting Basic Memory MCP server")
    mcp.run()