"""Parser for Basic Memory entity markdown files."""

import logging
from pathlib import Path

from basic_memory.markdown.exceptions import ParseError
from basic_memory.markdown.schemas import (
    Entity,
    EntityFrontmatter,
    EntityContent,
    EntityMetadata,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_sections(text):
    """Debug helper to show section contents."""
    sections = text.split("---\n")
    logger.debug("File sections:")
    for i, section in enumerate(sections):
        logger.debug(f"\n=== Section {i} ===\n{section.strip()}\n")
    return sections


class EntityParser:
    """Parser for entity markdown files."""

    def parse_file(self, path: Path, encoding: str = "utf-8") -> Entity:
        """Parse an entity markdown file."""
        if not path.exists():
            raise ParseError(f"File does not exist: {path}")

        try:
            # Read file content and split sections
            with open(path, "r", encoding=encoding) as f:
                raw_content = f.read()
            sections = debug_sections(raw_content)

            if len(sections) < 4:  # Needs at least empty,frontmatter,content,empty
                raise ParseError("Missing required document sections")

            # Parse each section using schema methods
            frontmatter = EntityFrontmatter.from_text(sections[1])
            content = EntityContent.from_markdown(sections[2])
            metadata = EntityMetadata.from_text(sections[4] if len(sections) >= 5 else "")

            return Entity(frontmatter=frontmatter, content=content, metadata=metadata)

        except UnicodeError as e:
            if encoding == "utf-8":
                return self.parse_file(path, encoding="utf-16")
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e
        except Exception as e:
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e