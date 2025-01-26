"""Process markdown files with structured sections.

This module follows a Read -> Modify -> Write pattern for all file operations:
1. Read entire file and parse into EntityMarkdown schema
2. Modify the schema (add relation, update content, etc)
3. Write entire file atomically using temp file + swap

No in-place updates are performed. Each write reconstructs the entire file from the schema.
The file format has two distinct types of content:
1. User content - Free form text that is preserved exactly as written
2. Structured sections - Observations and Relations that are always formatted
   in a standard way and can be overwritten since they're tracked in our schema
"""

from pathlib import Path
from typing import Optional

import frontmatter
from frontmatter import Post
from loguru import logger

from basic_memory import file_utils
from basic_memory.markdown.entity_parser import EntityParser
from basic_memory.markdown.schemas import EntityMarkdown, Observation, Relation


class DirtyFileError(Exception):
    """Raised when attempting to write to a file that has been modified."""

    pass


class MarkdownProcessor:
    """Process markdown files while preserving content and structure.

    This class handles the file I/O aspects of our markdown processing. It:
    1. Uses EntityParser for reading/parsing files into our schema
    2. Handles writing files with proper frontmatter
    3. Formats structured sections (observations/relations) consistently
    4. Preserves user content exactly as written
    5. Performs atomic writes using temp files

    It does NOT:
    1. Modify the schema directly (that's done by services)
    2. Handle in-place updates (everything is read->modify->write)
    3. Track schema changes (that's done by the database)
    """

    def __init__(self, entity_parser: EntityParser):
        """Initialize processor with base path and parser."""
        self.entity_parser = entity_parser

    async def read_file(self, path: Path) -> EntityMarkdown:
        """Read and parse file into EntityMarkdown schema.

        This is step 1 of our read->modify->write pattern.
        We use EntityParser to handle all the markdown parsing.
        """
        return await self.entity_parser.parse_file(path)

    async def write_file(
        self,
        path: Path,
        markdown: EntityMarkdown,
        expected_checksum: Optional[str] = None,
    ) -> str:
        """Write EntityMarkdown schema back to file.

        This is step 3 of our read->modify->write pattern.
        The entire file is rewritten atomically on each update.

        File Structure:
        ---
        frontmatter fields
        ---
        user content area (preserved exactly)

        ## Observations (if any)
        formatted observations

        ## Relations (if any)
        formatted relations

        Args:
            path: Where to write the file
            markdown: Complete schema to write
            expected_checksum: If provided, verify file hasn't changed

        Returns:
            Checksum of written file

        Raises:
            DirtyFileError: If file has been modified (when expected_checksum provided)
        """
        # Dirty check if needed
        if expected_checksum is not None:
            current_content = path.read_text()
            current_checksum = await file_utils.compute_checksum(current_content)
            if current_checksum != expected_checksum:
                raise DirtyFileError(f"File {path} has been modified")

        # Convert frontmatter to dict, dropping None values
        metadata = markdown.frontmatter.metadata or {}
        frontmatter_dict = {
            "type": markdown.frontmatter.type,
            "permalink": markdown.frontmatter.permalink,
            "created": markdown.frontmatter.created.isoformat() if markdown.frontmatter.created else None,
            "modified": markdown.frontmatter.modified.isoformat() if markdown.frontmatter.modified else None,
            **metadata
        }
        frontmatter_dict = {k: v for k, v in frontmatter_dict.items() if v is not None}

        # Start with user content (or minimal title for new files)
        content = markdown.content.content or f"# {markdown.frontmatter.title}\n"

        # Add structured sections if present
        if markdown.content.observations:
            content += (
                "\n\n## Observations\n\n"
                + self.format_observations(markdown.content.observations)
            )
        if markdown.content.relations:
            content += "\n## Relations\n\n" + self.format_relations(markdown.content.relations)

        # Create Post object for frontmatter
        post = Post(content, **frontmatter_dict)
        final_content = frontmatter.dumps(post)

        logger.debug(f"writing file {path} with content:\n{final_content}")

        # Write atomically and return checksum of updated file
        path.parent.mkdir(parents=True, exist_ok=True)
        await file_utils.write_file_atomic(path, final_content)
        return await file_utils.compute_checksum(final_content)

    def format_observations(self, observations: list[Observation]) -> str:
        """Format observations section in standard way.

        Format: - [category] content #tag1 #tag2 (context)
        """
        lines = [f"- {obs}" for obs in observations]
        return "\n".join(lines) + "\n"

    def format_relations(self, relations: list[Relation]) -> str:
        """Format relations section in standard way.

        Format: - relation_type [[target]] (context)
        """
        lines = [f"- {rel}" for rel in relations]
        return "\n".join(lines) + "\n"
