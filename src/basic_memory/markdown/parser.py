"""Parser for Basic Memory entity markdown files."""

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
    """
    Parser for entity markdown files.

    Entity files must have:
    - YAML frontmatter (type, id, created, modified, tags)
    - Title (# Title)
    - Optional description
    - Observations section (## Observations)
    - Relations section (## Relations)
    - Optional metadata section
    """

    async def parse_frontmatter(self, frontmatter: Dict[str, Any]) -> EntityFrontmatter:
        """
        Parse entity frontmatter.

        Args:
            frontmatter: Parsed YAML frontmatter

        Returns:
            Parsed EntityFrontmatter

        Raises:
            ParseError: If frontmatter doesn't match schema
        """
        try:
            # Preprocess fields for schema validation
            processed = frontmatter.copy()

            # Ensure id is string
            if "id" in processed:
                processed["id"] = str(processed["id"])

            # Handle tags field
            if "tags" in processed:
                if isinstance(processed["tags"], str):
                    # Split comma-separated tags and strip whitespace
                    processed["tags"] = [tag.strip() for tag in processed["tags"].split(",")]

            return EntityFrontmatter(**processed)

        except Exception as e:
            logger.error(f"Invalid entity frontmatter: {e}")
            raise ParseError(f"Invalid entity frontmatter: {str(e)}") from e

    async def parse_content(self, title: str, sections: Dict[str, str]) -> EntityContent:
        """
        Parse entity content section.

        Args:
            title: Document title
            sections: Section name -> content mapping

        Returns:
            Parsed EntityContent

        Raises:
            ParseError: If content sections are invalid
        """
        try:
            # Get description (if any)
            description = None
            if "description" in sections:
                description = sections["description"]

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
                title=title, description=description, observations=observations, relations=relations
            )

        except ParseError:
            raise
        except Exception as e:
            logger.error(f"Invalid entity content: {e}")
            raise ParseError(f"Invalid entity content: {str(e)}") from e

    async def parse_observation(self, line: str) -> Optional[Observation]:
        """
        Parse a single observation line.

        Format: [category] Content text #tag1 #tag2 (optional context)
        """
        if not line or line.isspace():
            return None

        try:
            # Extract category if present [category]
            category = None
            content = line
            if line.startswith("["):
                end_bracket = line.find("]")
                if end_bracket != -1:
                    category = line[1:end_bracket].strip()
                    content = line[end_bracket + 1 :].strip()

            # Extract context if present (context)
            context = None
            if content.endswith(")"):
                context_start = content.rfind("(")
                if context_start != -1:
                    context = content[context_start + 1 : -1].strip()
                    content = content[:context_start].strip()

            # Extract tags #tag1 #tag2
            tags = []
            content_parts = []
            for part in content.split():
                if part.startswith("#"):
                    tags.append(part[1:])  # Remove # prefix
                else:
                    content_parts.append(part)

            content = " ".join(content_parts).strip()

            if not content:
                logger.warning(f"Skipping observation with no content: {line}")
                return None

            return Observation(
                category=category, content=content, context=context, tags=tags if tags else None
            )

        except Exception as e:
            logger.warning(f"Failed to parse observation '{line}': {e}")
            return None

    async def parse_relation(self, line: str) -> Optional[Relation]:
        """
        Parse a single relation line.

        Format: relation_type [[Target Entity]] (optional context)
        """
        if not line or line.isspace():
            return None

        try:
            # Extract context if present (context)
            context = None
            main_part = line
            if line.endswith(")"):
                context_start = line.rfind("(")
                if context_start != -1:
                    context = line[context_start + 1 : -1].strip()
                    main_part = line[:context_start].strip()

            # Extract relation type and target [[Entity]]
            if "[[" not in main_part or "]]" not in main_part:
                logger.warning(f"Invalid relation format (missing [[]]): {line}")
                return None

            # Split into relation type and target
            relation_parts = main_part.split("[[", 1)
            relation_type = relation_parts[0].strip()
            if not relation_type:
                logger.warning(f"Missing relation type: {line}")
                return None

            target = relation_parts[1].split("]]")[0].strip()
            if not target:
                logger.warning(f"Missing target entity: {line}")
                return None

            return Relation(type=relation_type, target=target, context=context)

        except Exception as e:
            logger.warning(f"Failed to parse relation '{line}': {e}")
            return None

    async def parse_metadata(self, metadata: Optional[Dict[str, Any]]) -> EntityMetadata:
        """
        Parse entity metadata section.

        Args:
            metadata: Optional metadata dictionary

        Returns:
            Parsed EntityMetadata

        Raises:
            ParseError: If metadata doesn't match schema
        """
        try:
            if not metadata:
                return EntityMetadata()
            return EntityMetadata(metadata=metadata)
        except Exception as e:
            logger.error(f"Invalid entity metadata: {e}")
            raise ParseError(f"Invalid entity metadata: {str(e)}") from e

    async def create_document(
        self, frontmatter: EntityFrontmatter, content: EntityContent, metadata: EntityMetadata
    ) -> Entity:
        """
        Create entity from parsed sections.

        Args:
            frontmatter: Parsed frontmatter
            content: Parsed content
            metadata: Parsed metadata

        Returns:
            Complete entity
        """
        return Entity(frontmatter=frontmatter, content=content, metadata=metadata)
