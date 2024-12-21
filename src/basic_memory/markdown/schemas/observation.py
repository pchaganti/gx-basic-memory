"""Models for the markdown parser."""

import logging
import re
from typing import List, Optional

from pydantic import BaseModel

from basic_memory.markdown import ParseError

logging.basicConfig(level=logging.DEBUG)  # pragma: no cover
logger = logging.getLogger(__name__)  # pragma: no cover


class Observation(BaseModel):
    """An observation about an entity."""

    category: str
    content: str
    tags: List[str]
    context: Optional[str] = None

    @classmethod
    def from_line(cls, content: str) -> Optional["Observation"]:
        """Parse an observation line."""
        try:
            if not content.strip():
                return None

            try:
                if "\xff" in content or "\xfe" in content:
                    return None
            except UnicodeError:  # pragma: no cover
                return None

            # Only allow valid printable Unicode
            for char in content:
                # Skip normal whitespace
                if char in {" ", "\t", "\n", "\r"}:
                    continue
                if not char.isprintable():
                    return None

            # Break up extremely long content
            if len(content) > 10000:  # Arbitrary large limit
                logger.warning("Content too long, truncating: %s", content[:100])
                return None

            # Check for unclosed category first
            if "[" in content and "]" not in content:
                raise ParseError("unclosed category")

            # Then check for missing category
            match = re.match(r"^\s*(?:-\s*)?\[([^\]]*)\](.*)", content)
            if not match:
                raise ParseError("missing category")

            category = match.group(1).strip()
            if not category:
                return None

            content = match.group(2).strip()

            # Parse tags and content
            tags = []
            words = []
            for word in content.split():
                if word.startswith("#"):
                    # Handle #tag1#tag2#tag3
                    for tag in word.lstrip("#").split("#"):
                        if tag:
                            tags.append(tag)
                else:
                    words.append(word)

            content = " ".join(words)

            # Extract context
            context = None
            if content.endswith(")"):
                pos = content.find("(")
                if pos > 0:  # Must have content before paren
                    before = content[:pos].strip()
                    if before:
                        context = content[pos + 1 : -1].strip()
                        content = before

            return Observation(category=category, content=content, tags=tags, context=context)
        except ParseError:
            raise
        except Exception:
            logger.exception("Failed to parse observation: %s", content)  # pragma: no cover
            return None  # pragma: no cover
