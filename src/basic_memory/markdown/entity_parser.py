"""Universal parser for markdown files with optional frontmatter, observations, and relations.

The id field in frontmatter is derived from the filename, converted to snake_case with .md extension removed.
For example:
    'My Project Notes.md' -> 'my_project_notes'
    'API-Design.md' -> 'api_design'
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from loguru import logger

from basic_memory.markdown.base_parser import MarkdownParser, ParseError
from basic_memory.markdown.schemas import (
    EntityMarkdown,
    EntityFrontmatter,
    EntityContent,
    EntityMetadata,
    Observation,
    Relation,
)
from basic_memory.schemas.base import to_snake_case


class EntityParser(MarkdownParser[EntityMarkdown]):
    """A forgiving parser that extracts as much structure as it can find.
    
    Generates entity IDs from filenames by:
    1. Removing .md extension
    2. Converting to snake_case
    3. Removing any invalid characters
    """

    def convert_to_id(self, filename: str) -> str:
        """Convert a filename to a valid entity ID.
        
        Args:
            filename: Name of the file (with or without .md extension)
            
        Returns:
            Snake case version of filename without extension
            
        Examples:
            'My Project Notes.md' -> 'my_project_notes'
            'API-Design.md' -> 'api_design'
        """
        # Remove .md extension if present
        if filename.lower().endswith('.md'):
            filename = filename[:-3]
            
        return to_snake_case(filename)

    def parse_dates(self, frontmatter: Dict[str, Any], file_path: Path) -> Tuple[datetime, datetime]:
        """Parse created and updated dates from frontmatter or file system.
        
        Args:
            frontmatter: Dictionary containing frontmatter fields
            file_path: Path to the source file for fallback dates
            
        Returns:
            Tuple of (created_date, updated_date)
            
        Priority:
        1. Valid frontmatter dates
        2. File system dates (created/modified)
        """
        created = None
        updated = None
        
        # Try frontmatter first
        try:
            if 'created' in frontmatter:
                created = self.parse_date(frontmatter['created'])
            if 'updated' in frontmatter or 'modified' in frontmatter:
                updated = self.parse_date(frontmatter.get('updated') or frontmatter.get('modified'))
        except Exception as e:
            logger.warning(f"Error parsing frontmatter dates: {e}")

        # Fall back to file system dates if needed
        try:
            stats = file_path.stat()
            if not created:
                created = datetime.fromtimestamp(stats.st_ctime)
            if not updated:
                updated = datetime.fromtimestamp(stats.st_mtime)
        except Exception as e:
            logger.warning(f"Error getting file stats: {e}")
            # Last resort - use current time
            now = datetime.now()
            created = created or now
            updated = updated or now

        return created, updated

    def parse_date(self, value: Any) -> Optional[datetime]:
        """Convert various date formats to datetime."""
        if isinstance(value, datetime):
            return value
        try:
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
        return None

    def parse_tags(self, tags: Any) -> List[str]:
        """Convert various tag formats to list of strings."""
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        if isinstance(tags, (list, tuple)):
            return [str(t).strip() for t in tags if str(t).strip()]
        return []

    async def parse_frontmatter(self, frontmatter: Dict[str, Any], file_path: Optional[Path] = None) -> EntityFrontmatter:
        """Parse frontmatter with sensible defaults for missing fields.
        
        Args:
            frontmatter: Dictionary of frontmatter fields
            file_path: Optional path to source file, used for id and dates
        """
        try:
            # Get or generate ID from filename
            entity_name = None
            if file_path:
                entity_name = self.convert_to_id(file_path.name)
            
            # Get dates from frontmatter or file
            created, updated = self.parse_dates(frontmatter, file_path) if file_path else (datetime.now(), datetime.now())
            
            # Ensure we have minimum required fields
            processed = {
                "type": str(frontmatter.get("type", "document")).strip(),
                "id": str(frontmatter.get("id", entity_name or "document")).strip(),
                "created": created,
                "modified": updated,
                "tags": self.parse_tags(frontmatter.get("tags", []))
            }

            return EntityFrontmatter(**processed)

        except Exception as e:
            logger.warning(f"Error parsing frontmatter, using defaults: {e}")
            return EntityFrontmatter(
                type="document",
                id=entity_name or "document",
                created=created,
                modified=updated,
                tags=[]
            )

    async def parse_content(self, title: str, sections: Dict[str, str]) -> EntityContent:
        """Parse content sections without requiring any particular structure."""
        try:
            # Get content from content section if it exists
            content = sections.get("content", "").strip() or None

            # Try to parse observations if they exist
            observations = []
            if "observations" in sections:
                for line in sections["observations"].splitlines():
                    try:
                        obs = await self.parse_observation(line)
                        if obs:
                            observations.append(obs)
                    except ParseError as e:
                        logger.warning(f"Skipping invalid observation: {e}")

            # Try to parse relations if they exist
            relations = []
            if "relations" in sections:
                for line in sections["relations"].splitlines():
                    try:
                        rel = await self.parse_relation(line)
                        if rel:
                            relations.append(rel)
                    except ParseError as e:
                        logger.warning(f"Skipping invalid relation: {e}")

            # Also look for wiki-links in content as implicit relations
            try:
                content_relations = await self.parse_content_relations(sections.get("content", ""))
                relations.extend(content_relations)
            except Exception as e:
                logger.warning(f"Error parsing content relations: {e}")

            return EntityContent(
                title=title or "Untitled", 
                summary=content,
                observations=observations,
                relations=relations
            )

        except Exception as e:
            logger.error(f"Error parsing content, using minimal structure: {e}")
            return EntityContent(
                title=title or "Untitled",
                summary=None,
                observations=[],
                relations=[]
            )

    async def parse_observation(self, line: str) -> Optional[Observation]:
        """Parse a single observation line."""
        if not line or not line.strip().startswith("-"):
            return None

        line = line.strip()[1:].strip()  # Remove leading "-" and whitespace
        
        # Extract category if present
        category = None
        if line.startswith("["):
            end = line.find("]")
            if end != -1:
                category = line[1:end].strip()
                line = line[end + 1:].strip()

        # Extract context if present
        context = None
        if line.endswith(")"):
            start = line.rfind("(")
            if start != -1:
                context = line[start + 1:-1].strip()
                line = line[:start].strip()

        # Extract tags and content
        parts = line.split()
        content_parts = []
        tags = []
        
        for part in parts:
            if part.startswith("#"):
                tags.append(part[1:])
            else:
                content_parts.append(part)

        content = " ".join(content_parts).strip()
        if not content:
            return None

        return Observation(
            category=category,
            content=content,
            tags=tags if tags else None,
            context=context
        )

    async def parse_relation(self, line: str) -> Optional[Relation]:
        """Parse a single relation line."""
        if not line or not line.strip().startswith("-"):
            return None

        line = line.strip()[1:].strip()

        # Look for [[target]]
        start = line.find("[[")
        end = line.find("]]")
        if start == -1 or end == -1:
            return None

        # Extract parts
        rel_type = line[:start].strip() or "relates_to"  # Default type if none specified
        target = line[start + 2:end].strip()
        
        # Extract context if present
        context = None
        remaining = line[end + 2:].strip()
        if remaining.startswith("(") and remaining.endswith(")"):
            context = remaining[1:-1].strip()

        if not target:
            return None

        return Relation(
            type=rel_type,
            target=target,
            context=context
        )

    async def parse_content_relations(self, content: str) -> List[Relation]:
        """Extract wiki-style links from content as relations."""
        relations = []
        if not content:
            return relations

        import re
        pattern = r'\[\[([^\]]+)\]\]'
        
        for match in re.finditer(pattern, content):
            target = match.group(1).strip()
            if target:
                relations.append(Relation(
                    type="mentions",
                    target=target,
                    context=None
                ))

        return relations

    async def parse_metadata(self, metadata_section: Optional[str]) -> EntityMetadata:
        """Metadata section is no longer used."""
        return EntityMetadata()

    async def create_document(
        self,
        frontmatter: EntityFrontmatter,
        content: EntityContent,
        metadata: EntityMetadata
    ) -> EntityMarkdown:
        """Create the final EntityMarkdown document."""
        return EntityMarkdown(
            frontmatter=frontmatter,
            content=content,
            entity_metadata=metadata
        )