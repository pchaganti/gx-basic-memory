"""Tool for AI-assisted file editing."""

from pathlib import Path
from typing import List, Dict, Any

from basic_memory.mcp.server import mcp


def _detect_indent(text: str, match_pos: int) -> int:
    """Get indentation level at a position in text."""
    # Find start of line containing the match
    line_start = text.rfind("\n", 0, match_pos)
    if line_start < 0:
        line_start = 0
    else:
        line_start += 1  # Skip newline char

    # Count leading spaces
    pos = line_start
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos - line_start


def _apply_indent(text: str, spaces: int) -> str:
    """Apply indentation to text."""
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.split("\n"))


@mcp.tool()
async def ai_edit(path: str, edits: List[Dict[str, Any]]) -> bool:
    """AI-assisted file editing tool.

    Args:
        path: Path to file to edit
        edits: List of edits to apply. Each edit is a dict with:
            oldText: Text to replace
            newText: New content
            options: Optional dict with:
                indent: Number of spaces to indent
                preserveIndentation: Keep existing indent (default: true)

    Returns:
        bool: True if edits were applied successfully
    """
    try:
        # Read file
        content = Path(path).read_text()
        original = content
        success = True

        # Apply each edit
        for edit in edits:
            old_text = edit["oldText"]
            new_text = edit["newText"]
            options = edit.get("options", {})

            # Find text to replace
            match_pos = content.find(old_text)
            if match_pos < 0:
                success = False
                continue

            # Handle indentation
            if not options.get("preserveIndentation", True):
                # Use existing indentation
                indent = _detect_indent(content, match_pos)
                new_text = _apply_indent(new_text, indent)
            elif "indent" in options:
                # Use specified indentation
                new_text = _apply_indent(new_text, options["indent"])

            # Apply the edit
            content = content.replace(old_text, new_text)

        # Write back if changed
        if content != original:
            Path(path).write_text(content)
        return success

    except Exception as e:
        print(f"Error applying edits: {e}")
        return False
