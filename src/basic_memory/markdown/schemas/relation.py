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
    def parse_relation(cls, content: str) -> Optional["Relation"]:
        """Parse a relation line."""
        try:
            if not content.strip():
                return None

            # Check for unclosed [[
            if "[[" in content and "]]" not in content:
                raise ParseError("missing ]]")

            # Find the link
            match = re.search(r"\[\[([^\]]+)\]\]", content)
            if not match:
                raise ParseError("missing [[")

            target = match.group(1).strip()
            before_link = content[: match.start()].strip(" -")
            after_link = content[match.end() :].strip()

            # Everything before the link is the type
            rel_type = before_link.strip()
            if not rel_type:
                return None

            # Check for context in parentheses
            context = None
            if after_link.startswith("(") and after_link.endswith(")"):
                context = after_link[1:-1].strip()

            return Relation(target=target, type=rel_type, context=context)
        except ParseError:
            raise
        except Exception:
            logger.exception("Failed to parse relation: %s", content)
            return None
