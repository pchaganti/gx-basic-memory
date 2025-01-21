"""Note management tools for Basic Memory MCP server.

These tools provide a natural interface for working with markdown notes
while leveraging the underlying knowledge graph structure.
"""

from typing import Optional, List

from loguru import logger
from mcp.server.fastmcp.exceptions import ToolError

from basic_memory.mcp.server import mcp
from basic_memory.mcp.async_client import client
from basic_memory.mcp.tools.search import search
from basic_memory.schemas.request import CreateEntityRequest
from basic_memory.schemas.base import Entity, Relation
from basic_memory.schemas.request import CreateRelationsRequest
from basic_memory.mcp.tools.knowledge import create_entities, create_relations
from basic_memory.mcp.tools.utils import call_get
from basic_memory.schemas.search import SearchQuery


@mcp.tool(
    description="Create or update a markdown note. Returns the permalink for referencing.",
)
async def write_note(
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
) -> str:
    """Write a markdown note to the knowledge base.

    Args:
        title: The note's title
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
    logger.info(f"Writing note: {title}")

    # Create the entity request
    metadata = {"tags": [f"#{tag}" for tag in tags]} if tags else None
    request = CreateEntityRequest(
        entities=[
            Entity(
                title=title,
                entity_type="note",
                content_type="text/markdown",
                content=content,
                # Convert tags to observations if provided
                entity_metadata=metadata,
            )
        ]
    )

    # Use existing knowledge tool
    result = await create_entities(request)
    return result.entities[0].permalink


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
    try:
        # Try as permalink first
        response = await call_get(client, f"/resource/{identifier}")
        return response.text
    except ToolError as e:
        if "404" in str(e):
            # If not found, try searching by title
            search_response = await search(SearchQuery(text=identifier, entity_types=["note"]))

            if not search_response.results:
                raise ValueError(f"Note not found: {identifier}")

            # if we found results, return the first one
            response = await call_get(client, f"/resource/{search_response.results[0].permalink}")
            return response.text

        raise ValueError(f"Error reading note: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error reading note: {e}")


@mcp.tool(description="Create a semantic link between two notes")
async def link_notes(
    from_note: str,
    to_note: str,
    relationship: str = "relates_to",
    context: Optional[str] = None,
) -> None:
    """Create a semantic link between two notes.

    Args:
        from_note: Title or permalink of the source note
        to_note: Title or permalink of the target note
        relationship: Type of relationship (e.g., "relates_to", "implements", "depends_on")
        context: Optional context about the relationship

    Examples:
        # Create basic link
        link_notes(
            "Architecture Overview",
            "Implementation Details"
        )

        # Create specific relationship
        link_notes(
            "Project Requirements",
            "Technical Design",
            relationship="informs",
            context="Requirements drive technical decisions"
        )
    """
    request = CreateRelationsRequest(
        relations=[
            Relation(
                from_id=from_note,  # TODO: Add title->permalink lookup
                to_id=to_note,
                relation_type=relationship,
                context=context,
            )
        ]
    )
    await create_relations(request)
