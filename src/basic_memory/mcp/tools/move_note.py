"""Move note tool for Basic Memory MCP server."""

from textwrap import dedent
from typing import Optional

from loguru import logger

from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.utils import call_post
from basic_memory.mcp.project_session import get_active_project
from basic_memory.schemas import EntityResponse


def _format_move_error_response(error_message: str, identifier: str, destination_path: str) -> str:
    """Format helpful error responses for move failures that guide users to successful moves."""

    # Note not found errors
    if "entity not found" in error_message.lower() or "not found" in error_message.lower():
        search_term = identifier.split("/")[-1] if "/" in identifier else identifier
        title_format = (
            identifier.split("/")[-1].replace("-", " ").title() if "/" in identifier else identifier
        )
        permalink_format = identifier.lower().replace(" ", "-")

        return dedent(f"""
            # Move Failed - Note Not Found

            The note '{identifier}' could not be found for moving. Move operations require an exact match (no fuzzy matching).

            ## Suggestions to try:
            1. **Search for the note first**: Use `search_notes("{search_term}")` to find it with exact identifiers
            2. **Try different exact identifier formats**:
               - If you used a permalink like "folder/note-title", try the exact title: "{title_format}"
               - If you used a title, try the exact permalink format: "{permalink_format}"
               - Use `read_note()` first to verify the note exists and get the exact identifier

            3. **Check current project**: Use `get_current_project()` to verify you're in the right project
            4. **List available notes**: Use `list_directory("/")` to see what notes exist

            ## Before trying again:
            ```
            # First, verify the note exists:
            search_notes("{identifier}")

            # Then use the exact identifier from search results:
            move_note("correct-identifier-here", "{destination_path}")
            ```
            """).strip()

    # Destination already exists errors
    if "already exists" in error_message.lower() or "file exists" in error_message.lower():
        return f"""# Move Failed - Destination Already Exists

Cannot move '{identifier}' to '{destination_path}' because a file already exists at that location.

## How to resolve:
1. **Choose a different destination**: Try a different filename or folder
   - Add timestamp: `{destination_path.rsplit(".", 1)[0] if "." in destination_path else destination_path}-backup.md`
   - Use different folder: `archive/{destination_path}` or `backup/{destination_path}`

2. **Check the existing file**: Use `read_note("{destination_path}")` to see what's already there
3. **Remove or rename existing**: If safe to do so, move the existing file first

## Try these alternatives:
```
# Option 1: Add timestamp to make unique
move_note("{identifier}", "{destination_path.rsplit(".", 1)[0] if "." in destination_path else destination_path}-backup.md")

# Option 2: Use archive folder  
move_note("{identifier}", "archive/{destination_path}")

# Option 3: Check what's at destination first
read_note("{destination_path}")
```"""

    # Invalid path errors
    if "invalid" in error_message.lower() and "path" in error_message.lower():
        return f"""# Move Failed - Invalid Destination Path

The destination path '{destination_path}' is not valid: {error_message}

## Path requirements:
1. **Relative paths only**: Don't start with `/` (use `notes/file.md` not `/notes/file.md`)
2. **Include file extension**: Add `.md` for markdown files
3. **Use forward slashes**: For folder separators (`folder/subfolder/file.md`)
4. **No special characters**: Avoid `\\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`

## Valid path examples:
- `notes/my-note.md`
- `projects/2025/meeting-notes.md`
- `archive/old-projects/legacy-note.md`

## Try again with:
```
move_note("{identifier}", "notes/{destination_path.split("/")[-1] if "/" in destination_path else destination_path}")
```"""

    # Permission/access errors
    if (
        "permission" in error_message.lower()
        or "access" in error_message.lower()
        or "forbidden" in error_message.lower()
    ):
        return f"""# Move Failed - Permission Error

You don't have permission to move '{identifier}': {error_message}

## How to resolve:
1. **Check file permissions**: Ensure you have write access to both source and destination
2. **Verify project access**: Make sure you have edit permissions for this project
3. **Check file locks**: The file might be open in another application

## Alternative actions:
- Check current project: `get_current_project()`
- Switch projects if needed: `switch_project("project-name")`
- Try copying content instead: `read_note("{identifier}")` then `write_note()` to new location"""

    # Source file not found errors
    if "source" in error_message.lower() and (
        "not found" in error_message.lower() or "missing" in error_message.lower()
    ):
        return f"""# Move Failed - Source File Missing

The source file for '{identifier}' was not found on disk: {error_message}

This usually means the database and filesystem are out of sync.

## How to resolve:
1. **Check if note exists in database**: `read_note("{identifier}")`
2. **Run sync operation**: The file might need to be re-synced
3. **Recreate the file**: If data exists in database, recreate the physical file

## Troubleshooting steps:
```
# Check if note exists in Basic Memory
read_note("{identifier}")

# If it exists, the file is missing on disk - send a message to support@basicmachines.co
# If it doesn't exist, use search to find the correct identifier
search_notes("{identifier}")
```"""

    # Server/filesystem errors
    if (
        "server error" in error_message.lower()
        or "filesystem" in error_message.lower()
        or "disk" in error_message.lower()
    ):
        return f"""# Move Failed - System Error

A system error occurred while moving '{identifier}': {error_message}

## Immediate steps:
1. **Try again**: The error might be temporary
2. **Check disk space**: Ensure adequate storage is available
3. **Verify filesystem permissions**: Check if the destination directory is writable

## Alternative approaches:
- Copy content to new location: Use `read_note("{identifier}")` then `write_note()` 
- Use a different destination folder that you know works
- Send a message to support@basicmachines.co if the problem persists

## Backup approach:
```
# Read current content
content = read_note("{identifier}")

# Create new note at desired location  
write_note("New Note Title", content, "{destination_path.split("/")[0] if "/" in destination_path else "notes"}")

# Then delete original if successful
delete_note("{identifier}")
```"""

    # Generic fallback
    return f"""# Move Failed

Error moving '{identifier}' to '{destination_path}': {error_message}

## General troubleshooting:
1. **Verify the note exists**: `read_note("{identifier}")` or `search_notes("{identifier}")`
2. **Check destination path**: Ensure it's a valid relative path with `.md` extension
3. **Verify permissions**: Make sure you can edit files in this project
4. **Try a simpler path**: Use a basic folder structure like `notes/filename.md`

## Step-by-step approach:
```
# 1. Confirm note exists
read_note("{identifier}")

# 2. Try a simple destination first
move_note("{identifier}", "notes/{destination_path.split("/")[-1] if "/" in destination_path else destination_path}")

# 3. If that works, then try your original destination
```

## Alternative approach:
If moving continues to fail, you can copy the content manually:
```
# Read current content
content = read_note("{identifier}")

# Create new note
write_note("Title", content, "target-folder") 

# Delete original once confirmed
delete_note("{identifier}")
```"""


@mcp.tool(
    description="Move a note to a new location, updating database and maintaining links.",
)
async def move_note(
    identifier: str,
    destination_path: str,
    project: Optional[str] = None,
) -> str:
    """Move a note to a new file location within the same project.

    Args:
        identifier: Exact entity identifier (title, permalink, or memory:// URL).
                   Must be an exact match - fuzzy matching is not supported for move operations.
                   Use search_notes() or read_note() first to find the correct identifier if uncertain.
        destination_path: New path relative to project root (e.g., "work/meetings/2025-05-26.md")
        project: Optional project name (defaults to current session project)

    Returns:
        Success message with move details

    Examples:
        # Move to new folder (exact title match)
        move_note("My Note", "work/notes/my-note.md")
        
        # Move by exact permalink
        move_note("my-note-permalink", "archive/old-notes/my-note.md")
        
        # Specify project with exact identifier
        move_note("My Note", "archive/my-note.md", project="work-project")
        
        # If uncertain about identifier, search first:
        # search_notes("my note")  # Find available notes
        # move_note("docs/my-note-2025", "archive/my-note.md")  # Use exact result

    Note: This operation moves notes within the specified project only. Moving notes
    between different projects is not currently supported.

    The move operation:
    - Updates the entity's file_path in the database
    - Moves the physical file on the filesystem
    - Optionally updates permalinks if configured
    - Re-indexes the entity for search
    - Maintains all observations and relations
    """
    logger.debug(f"Moving note: {identifier} to {destination_path}")

    active_project = get_active_project(project)
    project_url = active_project.project_url

    try:
        # Prepare move request
        move_data = {
            "identifier": identifier,
            "destination_path": destination_path,
            "project": active_project.name,
        }

        # Call the move API endpoint
        url = f"{project_url}/knowledge/move"
        response = await call_post(client, url, json=move_data)
        result = EntityResponse.model_validate(response.json())

        # Build success message
        result_lines = [
            "✅ Note moved successfully",
            "",
            f"📁 **{identifier}** → **{result.file_path}**",
            f"🔗 Permalink: {result.permalink}",
            "📊 Database and search index updated",
            "",
            f"<!-- Project: {active_project.name} -->",
        ]

        # Log the operation
        logger.info(
            "Move note completed",
            identifier=identifier,
            destination_path=destination_path,
            project=active_project.name,
            status_code=response.status_code,
        )

        return "\n".join(result_lines)

    except Exception as e:
        logger.error(f"Move failed for '{identifier}' to '{destination_path}': {e}")
        # Return formatted error message for better user experience
        return _format_move_error_response(str(e), identifier, destination_path)
