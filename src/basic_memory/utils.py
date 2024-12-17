"""Utility functions for basic-memory."""

import re
import unicodedata


def sanitize_name(name: str) -> str:
    """
    Sanitize a name for filesystem use:
    - Convert to lowercase
    - Replace spaces/punctuation with underscores
    - Remove emojis and other special characters
    - Collapse multiple underscores
    - Trim leading/trailing underscores
    """
    # Normalize unicode to compose characters where possible
    name = unicodedata.normalize("NFKD", name)
    # Remove emojis and other special characters, keep only letters, numbers, spaces
    name = "".join(c for c in name if c.isalnum() or c.isspace())
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove newline
    name = name.replace("\n", "")
    # Convert to lowercase
    name = name.lower()
    # Collapse multiple underscores and trim
    name = re.sub(r"_+", "_", name).strip("_")

    return name
