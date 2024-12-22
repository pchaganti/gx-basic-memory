"""Models for the markdown parser."""
import logging
import re
from typing import List, Optional

from pydantic import BaseModel

from basic_memory.utils.file_utils import ParseError

logger = logging.getLogger(__name__)


class Observation(BaseModel):
    """An observation about an entity."""
    category: str
    content: str
    tags: List[str]
    context: Optional[str] = None

    @classmethod
    def from_line(cls, line: str) -> Optional["Observation"]:
        """
        Parse an observation from a line.

        Format must be:
        - [category] Content text #tag1 #tag2 (optional context)
        
        Leading spaces before bullet are allowed.
        """
        try:
            line = line.strip()
            
            # Skip empty or non-bullet lines
            if not line or not line.startswith("-"):
                return None

            # Remove bullet and trim
            line = line[1:].lstrip()

            # Parse category [category]
            match = re.match(r"\[([^\]]+)\](.*)", line)
            if not match:
                raise ParseError("Invalid format - must start with '[category]'")

            category = match.group(1).strip()
            if not category:
                raise ParseError("Category cannot be empty")

            rest = match.group(2).strip()

            # Parse content and tags
            content_parts = []
            tags = []
            context = None

            # Extract context if exists
            if rest.endswith(")"):
                context_start = rest.rfind("(")
                if context_start > 0:
                    context = rest[context_start + 1:-1].strip()
                    rest = rest[:context_start].strip()

            # Split remaining text and collect tags
            for word in rest.split():
                if word.startswith("#"):
                    tag = word[1:].strip()
                    if tag:
                        tags.append(tag)
                else:
                    content_parts.append(word)

            content = " ".join(content_parts)
            if not content:
                raise ParseError("Content cannot be empty")

            return cls(
                category=category,
                content=content,
                tags=tags,
                context=context,
            )

        except Exception as e:
            if not isinstance(e, ParseError):
                raise ParseError(f"Failed to parse observation: {line}: {str(e)}") from e
            raise