"""Base parser for markdown files with frontmatter."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, TypeVar, Generic, Optional, Dict, Any, Tuple

from loguru import logger

from basic_memory.utils.file_utils import parse_frontmatter, ParseError, FileError

T = TypeVar("T")  # The parsed document type


class MarkdownParser(ABC, Generic[T]):
    """Base parser for markdown files with frontmatter."""

    async def parse_file(self, path: Path, encoding: str = "utf-8") -> T:
        """
        Parse a markdown file with frontmatter.

        Args:
            path: Path to markdown file
            encoding: File encoding to use

        Returns:
            Parsed document of type T

        Raises:
            FileError: If file cannot be read
            ParseError: If content cannot be parsed
        """
        if not path.exists():
            raise FileError(f"File does not exist: {path}")

        try:
            content = path.read_text(encoding=encoding)
            return await self.parse_content_str(content)

        except UnicodeError as e:
            if encoding == "utf-8":
                return await self.parse_file(path, encoding="utf-16")
            raise ParseError(f"Failed to decode {path}: {str(e)}") from e

        except Exception as e:
            if not isinstance(e, (FileError, ParseError)):
                logger.error(f"Failed to parse {path}: {e}")
                raise ParseError(f"Failed to parse {path}: {str(e)}") from e
            raise

    async def parse_content_str(self, content: str) -> T:
        """
        Parse raw content string into document.

        Args:
            content: Raw file content

        Returns:
            Parsed document

        Raises:
            ParseError: If parsing fails
        """
        try:
            # Split into frontmatter and content
            frontmatter, markdown = await parse_frontmatter(content)

            # Parse frontmatter
            parsed_frontmatter = await self.parse_frontmatter(frontmatter)

            # Split remaining content into sections by headers
            title, sections = self._split_sections(markdown)
            if not title:
                raise ParseError("Missing title section (must start with #)")

            # Parse content sections
            parsed_content = await self.parse_content(title, sections)

            # Parse metadata section if present
            parsed_metadata = await self.parse_metadata(sections.get("metadata"))

            # Create final document
            return await self.create_document(
                frontmatter=parsed_frontmatter,
                content=parsed_content,
                metadata=parsed_metadata
            )

        except Exception as e:
            if not isinstance(e, ParseError):
                logger.error(f"Failed to parse content: {e}")
                raise ParseError(f"Failed to parse content: {str(e)}") from e
            raise

    def _split_sections(self, content: str) -> Tuple[Optional[str], Dict[str, str]]:
        """
        Split content into sections by headers.

        Args:
            content: Content section of the document

        Returns:
            Tuple of (title section, {section_name: section content})
        """
        # Initialize state
        title = None
        sections: Dict[str, str] = {}
        current_section = None
        current_lines: List[str] = []

        # Process each line
        for line in content.splitlines():
            line_stripped = line.strip()

            # Skip empty lines at start
            if not line_stripped and not title and not current_section:
                continue

            # Handle headers
            if line.startswith("# "):  # Top level header (title)
                # If we already have a title, this is a section (like # Metadata)
                if title:
                    # Save current section if any
                    if current_section and current_lines:
                        sections[current_section] = "\n".join(current_lines).strip()
                        current_lines = []
                    current_section = line[2:].strip().lower()
                else:
                    title = line[2:].strip()
                continue
            elif line.startswith("## "):  # Section header
                # Save current section if any
                if current_section and current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                    current_lines = []

                # Start new section
                current_section = line[3:].strip().lower()
                continue

            # Add line to current section
            if current_section is not None:
                current_lines.append(line)
            elif line_stripped and title:  # Non-empty line after title but before first section
                # Default section for content right after title
                if "content" not in sections:
                    sections["content"] = line_stripped
                else:
                    sections["content"] += f"\n{line_stripped}"

        # Save last section
        if current_section and current_lines:
            sections[current_section] = "\n".join(current_lines).strip()

        return title, sections

    @abstractmethod
    async def parse_frontmatter(self, frontmatter: Dict[str, Any]) -> Any:
        """Parse frontmatter section."""
        pass

    @abstractmethod
    async def parse_content(self, title: str, sections: Dict[str, str]) -> Any:
        """Parse content sections."""
        pass

    @abstractmethod
    async def parse_metadata(self, metadata: Optional[str]) -> Any:
        """Parse metadata section."""
        pass

    @abstractmethod
    async def create_document(self, frontmatter: Any, content: Any, metadata: Any) -> T:
        """Create document from parsed sections."""
        pass