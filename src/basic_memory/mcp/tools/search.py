"""Search tools for Basic Memory MCP server."""

from textwrap import dedent
from typing import List, Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.utils import call_post
from basic_memory.mcp.project_session import get_active_project
from basic_memory.schemas.search import SearchItemType, SearchQuery, SearchResponse


def _format_search_error_response(error_message: str, query: str, search_type: str = "text") -> str:
    """Format helpful error responses for search failures that guide users to successful searches."""

    # FTS5 syntax errors
    if "syntax error" in error_message.lower() or "fts5" in error_message.lower():
        clean_query = (
            query.replace('"', "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
            .replace("*", "")
        )
        return dedent(f"""
            # Search Failed - Invalid Syntax

            The search query '{query}' contains invalid syntax that the search engine cannot process.

            ## Common syntax issues:
            1. **Special characters**: Characters like `+`, `*`, `"`, `(`, `)` have special meaning in search
            2. **Unmatched quotes**: Make sure quotes are properly paired
            3. **Invalid operators**: Check AND, OR, NOT operators are used correctly

            ## How to fix:
            1. **Simplify your search**: Try using simple words instead: `{clean_query}`
            2. **Remove special characters**: Use alphanumeric characters and spaces
            3. **Use basic boolean operators**: `word1 AND word2`, `word1 OR word2`, `word1 NOT word2`

            ## Examples of valid searches:
            - Simple text: `project planning`
            - Boolean AND: `project AND planning`
            - Boolean OR: `meeting OR discussion`
            - Boolean NOT: `project NOT archived`
            - Grouped: `(project OR planning) AND notes`

            ## Try again with:
            ```
            search_notes("INSERT_CLEAN_QUERY_HERE")
            ```

            Replace INSERT_CLEAN_QUERY_HERE with your simplified search terms.
            """).strip()

    # No results found
    if "no results" in error_message.lower() or "not found" in error_message.lower():
        simplified_query = (
            " ".join(query.split()[:2])
            if len(query.split()) > 2
            else query.split()[0]
            if query.split()
            else "notes"
        )
        return dedent(f"""
            # Search Complete - No Results Found

            No content found matching '{query}' in the current project.

            ## Suggestions to try:
            1. **Broaden your search**: Try fewer or more general terms
               - Instead of: `{query}`
               - Try: `{simplified_query}`

            2. **Check spelling**: Verify terms are spelled correctly
            3. **Try different search types**:
               - Text search: `search_notes("{query}", search_type="text")`
               - Title search: `search_notes("{query}", search_type="title")`
               - Permalink search: `search_notes("{query}", search_type="permalink")`

            4. **Use boolean operators**:
               - Try OR search for broader results

            ## Check what content exists:
            - Recent activity: `recent_activity(timeframe="7d")`
            - List files: `list_directory("/")`
            - Browse by folder: `list_directory("/notes")` or `list_directory("/docs")`
            """).strip()

    # Server/API errors
    if "server error" in error_message.lower() or "internal" in error_message.lower():
        return dedent(f"""
            # Search Failed - Server Error

            The search service encountered an error while processing '{query}': {error_message}

            ## Immediate steps:
            1. **Try again**: The error might be temporary
            2. **Simplify the query**: Use simpler search terms
            3. **Check project status**: Ensure your project is properly synced

            ## Alternative approaches:
            - Browse files directly: `list_directory("/")`
            - Check recent activity: `recent_activity(timeframe="7d")`
            - Try a different search type: `search_notes("{query}", search_type="title")`

            ## If the problem persists:
            The search index might need to be rebuilt. Send a message to support@basicmachines.co or check the project sync status.
            """).strip()

    # Permission/access errors
    if (
        "permission" in error_message.lower()
        or "access" in error_message.lower()
        or "forbidden" in error_message.lower()
    ):
        return f"""# Search Failed - Access Error

You don't have permission to search in the current project: {error_message}

## How to resolve:
1. **Check your project access**: Verify you have read permissions for this project
2. **Switch projects**: Try searching in a different project you have access to
3. **Check authentication**: You might need to re-authenticate

## Alternative actions:
- List available projects: `list_projects()`
- Switch to accessible project: `switch_project("project-name")`
- Check current project: `get_current_project()`"""

    # Project not found errors
    if "project not found" in error_message.lower():
        return f"""# Search Failed - Project Not Found

The current project is not accessible or doesn't exist: {error_message}

## How to resolve:
1. **Check available projects**: `list_projects()`
2. **Switch to valid project**: `switch_project("valid-project-name")`
3. **Verify project setup**: Ensure your project is properly configured

## Current session info:
- Check current project: `get_current_project()`
- See available projects: `list_projects()`"""

    # Generic fallback
    return f"""# Search Failed

Error searching for '{query}': {error_message}

## General troubleshooting:
1. **Check your query**: Ensure it uses valid search syntax
2. **Try simpler terms**: Use basic words without special characters
3. **Verify project access**: Make sure you can access the current project
4. **Check recent activity**: `recent_activity(timeframe="7d")` to see if content exists

## Alternative approaches:
- Browse files: `list_directory("/")`
- Try different search type: `search_notes("{query}", search_type="title")`
- Search with filters: `search_notes("{query}", types=["entity"])`

## Need help?
- View recent changes: `recent_activity()`
- List projects: `list_projects()` 
- Check current project: `get_current_project()`"""


@mcp.tool(
    description="Search across all content in the knowledge base.",
)
async def search_notes(
    query: str,
    page: int = 1,
    page_size: int = 10,
    search_type: str = "text",
    types: Optional[List[str]] = None,
    entity_types: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    project: Optional[str] = None,
) -> SearchResponse | str:
    """Search across all content in the knowledge base.

    This tool searches the knowledge base using full-text search, pattern matching,
    or exact permalink lookup. It supports filtering by content type, entity type,
    and date.

    Args:
        query: The search query string
        page: The page number of results to return (default 1)
        page_size: The number of results to return per page (default 10)
        search_type: Type of search to perform, one of: "text", "title", "permalink" (default: "text")
        types: Optional list of note types to search (e.g., ["note", "person"])
        entity_types: Optional list of entity types to filter by (e.g., ["entity", "observation"])
        after_date: Optional date filter for recent content (e.g., "1 week", "2d")
        project: Optional project name to search in. If not provided, uses current active project.

    Returns:
        SearchResponse with results and pagination info

    Examples:
        # Basic text search
        results = await search_notes("project planning")

        # Boolean AND search (both terms must be present)
        results = await search_notes("project AND planning")

        # Boolean OR search (either term can be present)
        results = await search_notes("project OR meeting")

        # Boolean NOT search (exclude terms)
        results = await search_notes("project NOT meeting")

        # Boolean search with grouping
        results = await search_notes("(project OR planning) AND notes")

        # Search with type filter
        results = await search_notes(
            query="meeting notes",
            types=["entity"],
        )

        # Search with entity type filter, e.g., note vs
        results = await search_notes(
            query="meeting notes",
            types=["entity"],
        )

        # Search for recent content
        results = await search_notes(
            query="bug report",
            after_date="1 week"
        )

        # Pattern matching on permalinks
        results = await search_notes(
            query="docs/meeting-*",
            search_type="permalink"
        )

        # Search in specific project
        results = await search_notes("meeting notes", project="work-project")
    """
    # Create a SearchQuery object based on the parameters
    search_query = SearchQuery()

    # Set the appropriate search field based on search_type
    if search_type == "text":
        search_query.text = query
    elif search_type == "title":
        search_query.title = query
    elif search_type == "permalink" and "*" in query:
        search_query.permalink_match = query
    elif search_type == "permalink":
        search_query.permalink = query
    else:
        search_query.text = query  # Default to text search

    # Add optional filters if provided
    if entity_types:
        search_query.entity_types = [SearchItemType(t) for t in entity_types]
    if types:
        search_query.types = types
    if after_date:
        search_query.after_date = after_date

    active_project = get_active_project(project)
    project_url = active_project.project_url

    logger.info(f"Searching for {search_query}")

    try:
        response = await call_post(
            client,
            f"{project_url}/search/",
            json=search_query.model_dump(),
            params={"page": page, "page_size": page_size},
        )
        result = SearchResponse.model_validate(response.json())

        # Check if we got no results and provide helpful guidance
        if not result.results:
            logger.info(f"Search returned no results for query: {query}")
            # Don't treat this as an error, but the user might want guidance
            # We return the empty result as normal - the user can decide if they need help

        return result

    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        # Return formatted error message as string for better user experience
        return _format_search_error_response(str(e), query, search_type)
