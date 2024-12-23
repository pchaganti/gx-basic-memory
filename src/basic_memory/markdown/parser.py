"""Parser for Basic Memory entity markdown files."""

from datetime import datetime
import yaml
from typing import Dict, Any, Optional

from loguru import logger

from basic_memory.markdown.base_parser import MarkdownParser, ParseError
from basic_memory.markdown.schemas import (
    Entity,
    EntityFrontmatter,
    EntityContent,
    EntityMetadata,
    Observation,
    Relation,
)


class EntityParser(MarkdownParser[Entity]):
    """Parser for entity markdown files.

    Entity files must have:
    - YAML frontmatter (type, id, created, modified, tags)
    - Title (# Title)
    - Optional description
    - Observations section (## Observations)
    - Relations section (## Relations)
    - Optional # Metadata section with YAML between ---
    """

    async def parse_metadata(self, metadata_section: Optional[str]) -> EntityMetadata:
        """Parse metadata section."""
        try:
            if not metadata_section:
                return EntityMetadata()

            # Find YAML content between --- markers
            lines = metadata_section.strip().splitlines()
            yaml_lines = []
            in_yaml = False

            for line in lines:
                if line.strip() == "---":
                    in_yaml = not in_yaml  # Toggle state
                    continue
                if in_yaml:
                    yaml_lines.append(line)

            if not yaml_lines:
                return EntityMetadata()

            # Parse the YAML content
            try:
                yaml_content = yaml.safe_load("\n".join(yaml_lines))
                if not isinstance(yaml_content, dict):
                    logger.warning(f"Metadata YAML is not a dictionary: {yaml_content}")
                    return EntityMetadata()
                return EntityMetadata(data=yaml_content)
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse metadata YAML: {e}")
                return EntityMetadata()

        except Exception as e:
            logger.error(f"Failed to parse metadata: {e}")
            return EntityMetadata()

    async def parse_frontmatter(self, frontmatter: Dict[str, Any]) -> EntityFrontmatter:
        """Parse entity frontmatter."""
        try:
            # Check required fields
            required_fields = {"type", "id", "created", "modified"}
            missing = required_fields - set(frontmatter.keys())
            if missing:
                raise ParseError(f"Missing required frontmatter fields: {', '.join(missing)}")

            # Validate date fields
            for date_field in ["created", "modified"]:
                try:
                    if not isinstance(frontmatter[date_field], datetime):
                        datetime.fromisoformat(str(frontmatter[date_field]).replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    raise ParseError(f"Invalid date format for {date_field}: {frontmatter[date_field]}")

            # Prepare fields
            processed = {
                "type": frontmatter["type"].strip(),
                "id": str(frontmatter["id"]).strip(),
                "created": frontmatter["created"],
                "modified": frontmatter["modified"],
                "tags": (
                    [tag.strip() for tag in frontmatter.get("tags", "").split(",")]
                    if isinstance(frontmatter.get("tags"), str)
                    else [t.strip() for t in frontmatter.get("tags", [])]
                ),
            }

            return EntityFrontmatter(**processed)

        except Exception as e:
            if isinstance(e, ParseError):
                raise
            logger.error(f"Invalid entity frontmatter: {e}")
            raise ParseError(f"Invalid entity frontmatter: {str(e)}")

    async def parse_content(self, title: str, sections: Dict[str, str]) -> EntityContent:
        """Parse entity content section."""
        try:
            # Get description (if any)
            description = None
            if "content" in sections:
                description = sections["content"]

            # Parse observations (required)
            observations = []
            if "observations" not in sections:
                raise ParseError("Missing required observations section")

            for line in sections["observations"].splitlines():
                if line and not line.isspace():
                    observation = await self.parse_observation(line)
                    if observation:
                        observations.append(observation)

            # Parse relations (optional)
            relations = []
            if "relations" in sections:
                for line in sections["relations"].splitlines():
                    if line and not line.isspace():
                        relation = await self.parse_relation(line)
                        if relation:
                            relations.append(relation)

            return EntityContent(
                title=title,
                description=description,
                observations=observations,
                relations=relations
            )

        except ParseError:
            raise
        except Exception as e:
            logger.error(f"Invalid entity content: {e}")
            raise ParseError(f"Invalid entity content: {str(e)}")

    async def parse_observation(self, line: str) -> Optional[Observation]:
        """Parse a single observation line."""
        if not line or line.isspace():
            return None

        try:
            # Remove leading/trailing whitespace and bullet
            line = line.strip()
            if not line.startswith("-"):
                return None
            line = line[1:].strip()

            # Handle malformed category brackets first
            if line.startswith("]"):
                raise ParseError("missing category")
            elif line.startswith("["):
                close_bracket = line.find("]")
                if close_bracket == -1:
                    raise ParseError("unclosed category")

                # Extract category - return None for empty category
                category = line[1:close_bracket].strip()
                if not category:
                    return None

                content = line[close_bracket + 1:].strip()
            else:
                # No category brackets
                raise ParseError("missing category")

            # Extract context if present (context)
            context = None
            if content.endswith(")"):
                last_open = content.rfind("(")
                if last_open != -1:
                    # Check if these parentheses are part of content or a context marker
                    # by looking for hashtags between them
                    section_after_paren = content[last_open:]
                    if "#" not in section_after_paren:
                        context = content[last_open + 1 : -1].strip()
                        content = content[:last_open].strip()

            # Extract tags and clean content
            tags = []
            content_parts = []
            for part in content.split():
                if part.startswith("#"):
                    # Handle multiple hashtags stuck together
                    if "#" in part[1:]:
                        multi_tags = part.split("#")
                        tags.extend(t for t in multi_tags if t)
                    else:
                        tags.append(part[1:])
                else:
                    content_parts.append(part)

            content = " ".join(content_parts).strip()
            if not content:
                raise ParseError("Empty content")

            return Observation(
                category=category,
                content=content,
                tags=tags if tags else None,
                context=context
            )

        except ParseError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse observation: {e}")
            raise ParseError(f"Failed to parse observation: {str(e)}")

    async def parse_relation(self, line: str) -> Optional[Relation]:
        """Parse a single relation line."""
        if not line or line.isspace():
            return None

        try:
            # Remove leading/trailing whitespace and bullet
            line = line.strip()
            if not line.startswith("-"):
                return None
            line = line[1:].strip()

            # Extract context if present (context)
            context = None
            if line.endswith(")"):
                context_start = line.rfind("(")
                if context_start != -1:
                    context = line[context_start + 1 : -1].strip()
                    line = line[:context_start].strip()

            # Extract relation type and target [[Entity]]
            if "[[" not in line or "]]" not in line:
                raise ParseError("Invalid relation format - missing [[entity]]")

            # Split into relation type and target
            parts = line.split("[[", 1)
            rel_type = parts[0].strip()
            if not rel_type:
                raise ParseError("Missing relation type")

            target_part = parts[1]
            close_pos = target_part.find("]]")
            if close_pos == -1:
                raise ParseError("Unclosed [[ ]] in target")

            target = target_part[:close_pos].strip()
            if not target:
                raise ParseError("Empty target entity")

            return Relation(type=rel_type, target=target, context=context)

        except ParseError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse relation: {e}")
            raise ParseError(f"Failed to parse relation: {str(e)}")

    async def create_document(
        self, frontmatter: EntityFrontmatter, content: EntityContent, metadata: EntityMetadata
    ) -> Entity:
        """Create entity from parsed sections."""
        return Entity(
            frontmatter=frontmatter,
            content=content,
            metadata=metadata
        )