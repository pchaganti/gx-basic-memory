"""Models for the markdown parser."""
import logging
import re
from typing import Optional

from pydantic import BaseModel

from basic_memory.utils.file_utils import ParseError

logger = logging.getLogger(__name__)


class Relation(BaseModel):
    """A relation between entities."""
    type: str
    target: str
    context: Optional[str] = None

    @classmethod
    def from_line(cls, line: str) -> Optional["Relation"]:
        """
        Parse a relation from a line.

        Format must be:
        - relation_type [[Target Entity]] (optional context)
        """
        try:
            # Skip blank lines
            if not line.strip():
                return None

            # Remove leading/trailing whitespace and bullet
            line = line.strip()
            if not line.startswith("-"):
                return None
            line = line[1:].strip()

            # First, extract any context from parens at end
            context = None
            if line.endswith(")"):
                context_start = line.rfind("(")
                if context_start > 0:
                    context = line[context_start + 1:-1].strip()
                    line = line[:context_start].strip()

            # Look for relation_type [[target]]
            match = re.match(r"^(\w+)\s+\[\[([^\]]+)\]\]", line)
            if not match:
                raise ParseError("Invalid format - must be 'relation_type [[Target]]'")

            rel_type = match.group(1).strip()
            target = match.group(2).strip()

            if not rel_type:
                raise ParseError("Relation type cannot be empty")
            if not target:
                raise ParseError("Target cannot be empty")

            return cls(
                type=rel_type,
                target=target,
                context=context
            )

        except Exception as e:
            if not isinstance(e, ParseError):
                raise ParseError(f"Failed to parse relation: {line}: {str(e)}") from e
            raise