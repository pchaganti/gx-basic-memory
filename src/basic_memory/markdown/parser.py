"""Parser for Basic Memory entity markdown files."""

import logging
from pathlib import Path
from typing import List

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
        self.debug = False

    def parse_file(self, path: Path, encoding: str = "utf-8") -> Entity:
        """Parse an entity markdown file."""
        if not path.exists():
            raise ParseError(f"File does not exist: {path}")

        try:
            # Read file content
            with open(path, "r", encoding=encoding) as f:
                raw_content = f.read()

            # Split into sections and debug
            sections = debug_sections(raw_content)

            if len(sections) < 4:  # Needs at least empty,frontmatter,content,empty for no metadata
                raise ParseError("Missing required document sections")

            # Parse frontmatter (first yaml section)
            frontmatter_text = sections[1].strip()
            frontmatter_data = {}

            for line in frontmatter_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter_data[key.strip()] = value.strip()

            if isinstance(frontmatter_data.get("tags"), str):
                frontmatter_data["tags"] = [t.strip() for t in frontmatter_data["tags"].split(",")]

            frontmatter = EntityFrontmatter(**frontmatter_data)

            # Parse markdown content (middle section)
            content_tokens = self.md.parse(sections[2].strip())

            # State for content parsing
            title = ""
            description = ""
            observations: List[Observation] = []
            relations: List[Relation] = []
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
                            if obs := Observation.parse_observation(item_content):
                                observations.append(obs)
                        elif current_section == "relations":
                            if rel := Relation.parse_relation(item_content):
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

            # Parse metadata (final section if exists)
            metadata = {}
            if len(sections) >= 5:  # Has backmatter section
                metadata_text = sections[4].strip()
                logger.debug(f"Metadata text: {metadata_text}")
                for line in metadata_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()

            metadata_obj = EntityMetadata(metadata=metadata)

            return Entity(frontmatter=frontmatter, content=content, metadata=metadata_obj)

        except UnicodeError as e:
            if encoding == "utf-8":
                return self.parse_file(path, encoding="utf-16")
            raise ParseError(f"Failed to read {path} with encoding {encoding}: {str(e)}")
        except Exception as e:
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e
