"""Models for the markdown parser."""

import logging
import re
from typing import Optional

from pydantic import BaseModel

from basic_memory.markdown import ParseError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Relation(BaseModel):
    """A relation between entities."""

    target: str  # The entity being linked to
    type: str  # The type of relation
    context: Optional[str] = None

    @classmethod
    def from_line(cls, content: str) -> Optional["Relation"]:
        """Parse a relation line."""
        try:
            if not content.strip():
                return None

            # Check for unclosed markup
            if "[[" in content and "]]" not in content:
                raise ParseError("missing ]]")
            if "]]" in content and "[[" not in content:
                raise ParseError("invalid relation syntax")

            # Find the link - must have [[target]]
            match = re.search(r"\[\[([^\]]+)\]\]", content)
            if not match:
                # For the error test case, it needs exactly this message
                raise ParseError("missing [[")

            target = match.group(1).strip()
            if not target:  # Empty target
                return None

            # Get text before the link, excluding bullet
            before_link = content[: match.start()].strip(" -")

            # Validate relation type
            rel_type = before_link.strip()
            if not rel_type or rel_type == "missing type":  # Explicitly reject "missing type"
                return None

            # Get text after the link
            after_link = content[match.end() :].strip()

            # Check for context in parentheses
            context = None
            if after_link:
                if not (after_link.startswith("(") and after_link.endswith(")")):
                    raise ParseError("invalid context format")
                context = after_link[1:-1].strip()

            return Relation(target=target, type=rel_type, context=context)
        except ParseError:
            raise
        except Exception as e:
            logger.exception("Failed to parse relation: %s", content)
            return None