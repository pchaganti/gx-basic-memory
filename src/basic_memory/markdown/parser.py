"""Parser for Basic Memory entity markdown files."""

import logging
import re
from pathlib import Path
from typing import Optional, List, Tuple, Dict

import frontmatter
from markdown_it import MarkdownIt

from basic_memory.markdown.exceptions import ParseError
from basic_memory.markdown.models import (
    Observation,
    Relation,
    Entity,
    EntityFrontmatter,
    EntityContent,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class EntityParser:
    """Parser for entity markdown files."""

    def __init__(self):
        self.md = MarkdownIt()

    def _parse_observation(self, content: str) -> Optional[Observation]:
        """Parse an observation line."""
        try:
            if not content.strip():
                return None

            # Check for unclosed bracket first
            if "[" in content and "]" not in content:
                raise ParseError("unclosed category")

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

    def _parse_relation(self, content: str) -> Optional[Relation]:
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

    def _parse_metadata_line(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse a metadata line into key-value pair."""
        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        return key.strip(), value.strip()

    def parse_file(self, path: Path, encoding: str = "utf-8") -> Entity:
        """Parse an entity markdown file."""
        if not path.exists():
            raise ParseError(f"File does not exist: {path}")

        try:
            # Read and parse frontmatter
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
                post = frontmatter.loads(content)

            # Handle frontmatter
            metadata = dict(post.metadata)
            if isinstance(metadata.get("tags"), str):
                metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]
            frontmatter_data = EntityFrontmatter(**metadata)

            # Parse markdown
            tokens = self.md.parse(post.content)

            # State for parsing
            title = ""
            description = ""
            observations: List[Observation] = []
            relations: List[Relation] = []
            context = ""
            metadata = {}
            
            current_section = None
            description_tokens = []

            # Track list item state
            in_list_item = False
            list_item_tokens = []
            list_item_level = None
            base_list_level = None

            # Track metadata continuation state
            current_meta_key = None
            current_meta_value = []

            for token in tokens:
                if token.type == "heading_open":
                    # Handle any pending metadata
                    if current_meta_key:
                        metadata[current_meta_key] = " ".join(current_meta_value).strip()
                        current_meta_key = None
                        current_meta_value = []

                    if token.tag == "h1":
                        current_section = "title"
                    elif token.tag == "h2":
                        # Handle previous section
                        if current_section == "description":
                            description = " ".join(t.content for t in description_tokens)
                        current_section = "section_name"
                        description_tokens = []
                
                elif token.type == "inline":
                    content = token.content.strip()
                    
                    if current_section == "title":
                        title = content
                        current_section = "description"
                    elif current_section == "section_name":
                        section = content.lower()
                        if section == "description":
                            description_tokens = []
                        current_section = section
                    elif current_section == "description":
                        description_tokens.append(token)
                    elif current_section == "metadata":
                        # Parse metadata line
                        if ":" in content:
                            # Save previous key if exists
                            if current_meta_key:
                                metadata[current_meta_key] = " ".join(current_meta_value).strip()
                            # Start new key
                            key, value = content.split(":", 1)
                            current_meta_key = key.strip()
                            current_meta_value = [value.strip()]
                        elif content.strip() and current_meta_key:
                            # Continue previous value
                            current_meta_value.append(content.strip())
                    elif in_list_item:
                        list_item_tokens.append(token)
                
                elif token.type == "list_item_open":
                    in_list_item = True
                    list_item_level = token.level
                    if base_list_level is None:
                        base_list_level = token.level
                    list_item_tokens = []
                
                elif token.type == "list_item_close" and in_list_item:
                    # Only process top-level items
                    if base_list_level is None or list_item_level == base_list_level:
                        item_content = " ".join(t.content for t in list_item_tokens)
                        try:
                            if current_section == "observations":
                                if obs := self._parse_observation(item_content):
                                    observations.append(obs)
                            elif current_section == "relations":
                                if rel := self._parse_relation(item_content):
                                    relations.append(rel)
                        except ParseError:
                            # Skip malformed items
                            pass
                    in_list_item = False
                    list_item_tokens = []

            # Handle any remaining description
            if current_section == "description" and description_tokens:
                description = " ".join(t.content for t in description_tokens)

            # Handle any remaining metadata
            if current_meta_key:
                metadata[current_meta_key] = " ".join(current_meta_value).strip()

            # Create entity
            content_data = EntityContent(
                title=title,
                description=description,
                observations=observations,
                relations=relations,
                context=context,
                metadata=metadata,
            )

            return Entity(frontmatter=frontmatter_data, content=content_data)

        except UnicodeError as e:
            if encoding == "utf-8":
                return self.parse_file(path, encoding="utf-16")
            raise ParseError(f"Failed to read {path} with encoding {encoding}: {str(e)}")
        except Exception as e:
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e