"""Note management tools for Basic Memory MCP server.

These tools provide a natural interface for working with markdown notes
while leveraging the underlying knowledge graph structure.
"""

from typing import Optional, List

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.mcp.async_client import client
from basic_memory.schemas import EntityResponse, DeleteEntitiesResponse
from basic_memory.schemas.base import Entity
from basic_memory.mcp.tools.utils import call_get, call_put, call_delete


@mcp.tool(
    description="Create or update a markdown note. Returns the permalink for referencing.",
)
async def write_note(
    file_path: str,
    content: str,
    tags: Optional[List[str]] = None,
) -> str:
    """Write a markdown note to the knowledge base.

    Args:
        file_path: The note's title
        content: Markdown content for the note
        tags: Optional list of tags to categorize the note

    Returns:
        Permalink that can be used to reference the note

    Examples:
        # Create a simple note
        write_note(
            title="Meeting Notes: Project Planning",
            content="# Key Points\\n\\n- Discussed timeline\\n- Set priorities"
        )

        # Create note with tags
        write_note(
            title="Security Review",
            content="# Findings\\n\\n1. Updated auth flow\\n2. Added rate limiting",
            tags=["security", "development"]
        )
    """
    logger.info(f"Writing note: {file_path}")

    # Create the entity request
    metadata = {"tags": [f"#{tag}" for tag in tags]} if tags else None
    entity = Entity(
        file_path=file_path,
        entity_type="note",
        content_type="text/markdown",
        content=content,
        entity_metadata=metadata,
    )

    # Use existing knowledge tool
    logger.info(f"Creating {entity.permalink}")
    url = f"/knowledge/entities/{entity.permalink}"
    response = await call_put(client, url, json=entity.model_dump())
    result = EntityResponse.model_validate(response.json())
    return result.permalink


@mcp.tool(description="Read a note's content by its title or permalink")
async def read_note(identifier: str) -> str:
    """Get the markdown content of a note.
    Uses the resource router to return the actual file content.

    Args:
        identifier: Note title or permalink

    Returns:
        The note's markdown content

    Examples:
        # Read by title
        read_note("Meeting Notes: Project Planning")

        # Read by permalink
        read_note("notes/project-planning")

    Raises:
        ValueError: If the note cannot be found
    """
    response = await call_get(client, f"/resource/{identifier}")
    return response.text


@mcp.tool(description="Delete a note by title or permalink")
async def delete_note(identifier: str) -> bool:
    """Delete a note from the knowledge base.

    Args:
        identifier: Note title or permalink

    Returns:
        True if note was deleted, False otherwise

    Examples:
        # Delete by title
        delete_note("Meeting Notes: Project Planning")

        # Delete by permalink
        delete_note("notes/project-planning")
    """
    response = await call_delete(client, f"/knowledge/entities/{identifier}")
    result = DeleteEntitiesResponse.model_validate(response.json())
    return result.deleted
