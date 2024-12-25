"""Basic Memory MCP server using fastmcp - proxies to FastAPI endpoints."""

import sys
from typing import Any, List, Optional, Dict

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
async def create_entities(entities: List[dict]) -> dict:
    """Create new entities in the knowledge graph.

    Args:
        entities: List of entity dictionaries, each containing:
            - name: Entity name
            - entity_type: Classification (e.g., 'component', 'specification')
            - description: Optional description
            - observations: Optional list of initial observations

    Example:
        create_entities([{
            "name": "Knowledge Format",
            "entity_type": "specification",
            "description": "Document format specification",
            "observations": ["Uses markdown format", "Supports YAML frontmatter"]
        }])
    """
    url = "/knowledge/entities"
    data = {"entities": entities}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def create_relations(relations: List[dict]) -> dict:
    """Create relations between existing entities.

    Args:
        relations: List of relation dictionaries, each containing:
            - from_id: Source entity path_id
            - to_id: Target entity path_id
            - relation_type: Type of relationship in active voice
            - context: Optional context for the relation

    Example:
        create_relations([{
            "from_id": "test/parser_test",
            "to_id": "component/parser",
            "relation_type": "validates",
            "context": "Unit test coverage"
        }])
    """
    url = "/knowledge/relations"
    data = {"relations": relations}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def add_observations(path_id: str, observations: List[dict], context: Optional[str] = None) -> dict:
    """Add observations to an entity.

    Args:
        path_id: Entity path ID
        observations: List of observations, each containing:
            - content: The observation text
            - category: Optional category ('tech', 'design', 'feature', 'note', 'issue', 'todo')
        context: Optional shared context for all observations

    Example:
        add_observations(
            "specification/knowledge_format",
            observations=[
                {"content": "Uses markdown format", "category": "tech"},
                {"content": "Designed for readability", "category": "design"}
            ],
            context="Initial design"
        )
    """
    url = "/knowledge/observations"
    data = {
        "path_id": path_id,
        "observations": observations,
        "context": context
    }
    response = await client.post(url, json=data)
    await log_api_call("POST", url, data, response)
    return response.json()


## Read endpoints


@mcp.tool()
async def get_entity(path_id: str) -> dict:
    """Get a specific entity by its path_id.

    Args:
        path_id: Entity path ID (e.g., 'component/memory_service')

    Returns:
        Complete entity information including observations and relations.

    Example:
        get_entity("specification/knowledge_format")
    """
    url = f"/knowledge/entities/{path_id}"
    response = await client.get(url)
    return response.json()


@mcp.tool()
async def search_nodes(query: str, category: Optional[str] = None) -> dict:
    """Search for entities in the knowledge graph.

    Args:
        query: Search text to match against entities
        category: Optional category to filter observations by

    Returns:
        Matching entities with their observations and relations.

    Example:
        search_nodes("markdown format", category="tech")  # Find tech observations about markdown
        search_nodes("implementation")  # Search all categories
    """
    url = "/knowledge/search"
    data = {"query": query, "category": category}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def open_nodes(path_ids: List[str]) -> dict:
    """Load multiple entities by their path_ids.

    Args:
        path_ids: List of entity path IDs to load

    Returns:
        Dictionary of loaded entities with their observations and relations.

    Example:
        open_nodes([
            "specification/knowledge_format",
            "component/parser"
        ])
    """
    url = "/knowledge/nodes"
    data = {"path_ids": path_ids}
    response = await client.post(url, json=data)
    return response.json()


## Delete endpoints


@mcp.tool()
async def delete_entities(path_ids: List[str]) -> dict:
    """Delete entities from the knowledge graph.

    Args:
        path_ids: List of entity path IDs to delete

    Example:
        delete_entities(["test/obsolete_test", "component/old_component"])
    """
    url = "/knowledge/entities/delete"
    data = {"path_ids": path_ids}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def delete_observations(path_id: str, observations: List[str]) -> dict:
    """Delete specific observations from an entity.

    Args:
        path_id: Entity path ID
        observations: List of observation content strings to delete

    Example:
        delete_observations(
            "component/parser",
            ["Obsolete implementation detail", "Old design note"]
        )
    """
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
async def delete_relations(relations: List[dict]) -> dict:
    """Delete relations between entities.

    Args:
        relations: List of relation dictionaries to delete, each containing:
            - from_id: Source entity path_id
            - to_id: Target entity path_id
            - relation_type: Type of relationship

    Example:
        delete_relations([{
            "from_id": "test/old_test",
            "to_id": "component/parser",
            "relation_type": "validates"
        }])
    """
    url = "/knowledge/relations/delete"
    data = {"relations": relations}
    response = await client.post(
        url, json=data
    )
    return response.json()


# Document Tools


@mcp.tool()
async def create_document(path: str, content: str, metadata: Optional[Dict] = None) -> dict:
    """Create a new document.

    Args:
        path: Document path (must end in .md)
        content: Document content as markdown text
        metadata: Optional metadata dictionary

    Example:
        create_document(
            "docs/format.md",
            "# Format Specification\n\nDetails here...",
            metadata={"author": "AI team"}
        )
    """
    url = "/documents/create"
    data = {"path": path, "content": content, "metadata": metadata}
    response = await client.post(url, json=data)
    return response.json()


@mcp.tool()
async def get_document(path: str) -> dict:
    """Get a document by its path.

    Args:
        path: Document path to retrieve

    Example:
        get_document("docs/format.md")
    """
    url = f"/documents/{path}"
    response = await client.get(url)
    return response.json()


@mcp.tool()
async def update_document(path: str, content: str, metadata: Optional[Dict] = None) -> dict:
    """Update an existing document.

    Args:
        path: Document path
        content: New document content
        metadata: Optional new metadata

    Example:
        update_document(
            "docs/format.md",
            "# Updated Format\n\nNew content...",
            metadata={"updated_by": "AI team"}
        )
    """
    url = f"/documents/{path}"
    data = {"path": path, "content": content, "metadata": metadata}
    response = await client.put(url, json=data)
    return response.json()


@mcp.tool()
async def list_documents() -> list:
    """List all documents in the system.

    Returns:
        List of document paths and metadata.

    Example:
        list_documents()  # Get all document paths
    """
    url = "/documents/list"
    response = await client.get(url)
    return response.json()


@mcp.tool()
async def delete_document(path: str) -> dict:
    """Delete a document.

    Args:
        path: Path of document to delete

    Example:
        delete_document("docs/obsolete.md")
    """
    url = f"/documents/{path}"
    response = await client.delete(url)
    if response.status_code == 204:
        return {"deleted": True}

if __name__ == "__main__":
    setup_logging()
    logger.info("Starting Basic Memory MCP server")
    mcp.run()
