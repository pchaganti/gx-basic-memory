"""Parser for Basic Memory entity markdown files."""

import logging
from pathlib import Path

from markdown_it import MarkdownIt

from basic_memory.markdown.exceptions import ParseError
from basic_memory.markdown.schemas import (
    Observation,
    Relation,
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

    def __init__(self):
        self.md = MarkdownIt()

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

            # Parse markdown content (middle section)
            content_tokens = self.md.parse(sections[2].strip())

            # State for content parsing
            title = ""
            description = ""
            observations = []
            relations = []
            current_section = None

            # Track list items
            in_list_item = False
            list_item_tokens = []

            for token in content_tokens:
                if token.type == "heading_open":
                    if token.tag == "h1":
                        current_section = "title"
                    elif token.tag == "h2":
                        current_section = "section_name"

                elif token.type == "inline":
                    content = token.content.strip()

                    if current_section == "title":
                        title = content
                        current_section = "description"
                    elif current_section == "section_name":
                        current_section = content.lower()
                    elif current_section == "description":
                        if description:
                            description += " "
                        description += content
                    elif in_list_item:
                        list_item_tokens.append(token)

                elif token.type == "list_item_open":
                    in_list_item = True
                    list_item_tokens = []

                elif token.type == "list_item_close":
                    item_content = " ".join(t.content for t in list_item_tokens)
                    try:
                        if current_section == "observations":
                            if obs := Observation.from_line(item_content):
                                observations.append(obs)
                        elif current_section == "relations":
                            if rel := Relation.from_line(item_content):
                                relations.append(rel)
                    except ParseError:
                        # Skip malformed items
                        pass
                    in_list_item = False

            # Create content object
            content = EntityContent(
                title=title,
                description=description,
                observations=observations,
                relations=relations,
            )

            # Parse metadata from final section
            metadata_obj = EntityMetadata(metadata={})
            if len(sections) >= 5:
                metadata_text = sections[4].strip()
                logger.debug(f"Metadata text: {metadata_text}")
                for line in metadata_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata_obj.metadata[key.strip()] = value.strip()

            return Entity(frontmatter=frontmatter, content=content, metadata=metadata_obj)

        except UnicodeError as e:
            if encoding == "utf-8":
                return self.parse_file(path, encoding="utf-16")
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e
        except Exception as e:
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e