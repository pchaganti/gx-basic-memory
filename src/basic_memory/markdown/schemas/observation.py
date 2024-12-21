"""Models for the markdown parser."""

import logging
import re
from typing import List, Optional

from pydantic import BaseModel

from basic_memory.markdown import ParseError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Observation(BaseModel):
    """An observation about an entity."""

    category: str
    content: str
    tags: List[str]
    context: Optional[str] = None

    @classmethod
    def parse_observation(cls, content: str) -> Optional["Observation"]:
        """Parse an observation line."""
        try:
            if not content.strip():
                return None

            # Parse category [type]
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

            # Extract context in parentheses
            context = None
            if content.endswith(")"):
                ctx_start = content.rfind("(")
                if ctx_start != -1:
                    context = content[ctx_start + 1 : -1].strip()
                    content = content[:ctx_start].strip()

            return Observation(category=category, content=content, tags=tags, context=context)
        except ParseError:
            raise
        except Exception:
            logger.exception("Failed to parse observation: %s", content)
            return None
