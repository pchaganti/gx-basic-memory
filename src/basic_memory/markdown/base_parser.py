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
            frontmatter, remaining = await parse_frontmatter(content)

            # Split main content into sections
            title, sections = self.split_sections(remaining)
            if not title:
                raise ParseError("Missing title section (must start with #)")

            # Parse each section
            parsed_frontmatter = await self.parse_frontmatter(frontmatter)
            parsed_content = await self.parse_content(title, sections)
            parsed_metadata = await self.parse_metadata(frontmatter.get("metadata"))

            # Create document from parts
            return await self.create_document(parsed_frontmatter, parsed_content, parsed_metadata)

        except Exception as e:
            if not isinstance(e, ParseError):
                logger.error(f"Failed to parse content: {e}")
                raise ParseError(f"Failed to parse content: {str(e)}") from e
            raise

    def split_sections(self, content: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Split content into sections by headers.

        Args:
            content: Content section of the document

        Returns:
            Tuple of (title section, {section_name: list of section lines})
        """
        current_section = None
        sections = {}
        title = None

        for line in content.splitlines():
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Handle headers
            if line.startswith("#"):
                # Top level header is title
                if line.startswith("# "):
                    title = line[2:].strip()
                    continue

                # Other headers start new sections
                if line.startswith("## "):
                    current_section = line[3:].strip().lower()
                    sections[current_section] = []
                    continue

            # Add non-header lines to current section
            if current_section:
                sections[current_section].append(line)

        return title, sections  # pyright: ignore [reportReturnType]

    @abstractmethod
    async def parse_frontmatter(self, frontmatter: Dict[str, Any]) -> Any:
        """Parse frontmatter section."""
        pass

    @abstractmethod
    async def parse_content(self, title: str, sections: Dict[str, List[str]]) -> Any:
        """Parse content sections."""
        pass

    @abstractmethod
    async def parse_metadata(self, metadata: Optional[Dict[str, Any]]) -> Any:
        """Parse metadata section."""
        pass

    @abstractmethod
    async def create_document(self, frontmatter: Any, content: Any, metadata: Optional[Any]) -> T:
        """Create document from parsed sections."""
        pass
