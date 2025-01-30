"""Utilities for file operations."""
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple

import yaml
from loguru import logger


class FileError(Exception):
    """Base exception for file operations."""
    pass


class FileWriteError(FileError):
    """Raised when file operations fail."""
    pass


class ParseError(FileError):
    """Raised when parsing file content fails."""
    pass


async def compute_checksum(content: str) -> str:
    """
    Compute SHA-256 checksum of content.
    
    Args:
        content: Text content to hash
        
    Returns:
        SHA-256 hex digest
        
    Raises:
        FileError: If checksum computation fails
    """
    try:
        return hashlib.sha256(content.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute checksum: {e}")
        raise FileError(f"Failed to compute checksum: {e}")


async def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, creating if necessary.
    
    Args:
        path: Directory path to ensure
        
    Raises:
        FileWriteError: If directory creation fails
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory: {path}: {e}")
        raise FileWriteError(f"Failed to create directory {path}: {e}")


async def write_file_atomic(path: Path, content: str) -> None:
    """
    Write file with atomic operation using temporary file.
    
    Args:
        path: Target file path
        content: Content to write
        
    Raises:
        FileWriteError: If write operation fails
    """
    temp_path = path.with_suffix(".tmp")
    try:
        temp_path.write_text(content)
        
        # TODO check for path.exists()
        temp_path.replace(path)
        logger.debug(f"wrote file: {path}")
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        logger.error(f"Failed to write file: {path}: {e}")
        raise FileWriteError(f"Failed to write file {path}: {e}")


def has_frontmatter(content: str) -> bool:
    """
    Check if content contains YAML frontmatter.

    Args:
        content: Content to check

    Returns:
        True if content has frontmatter delimiter (---), False otherwise
    """
    content = content.strip()
    return content.startswith("---") and "---" in content[3:]


def parse_frontmatter(content: str) -> Dict[str, Any]:
    """
    Parse YAML frontmatter from content.

    Args:
        content: Content with YAML frontmatter

    Returns:
        Dictionary of frontmatter values

    Raises:
        ParseError: If frontmatter is invalid or parsing fails
    """
    try:
        if not has_frontmatter(content):
            raise ParseError("Content has no frontmatter")

        # Split on first two occurrences of ---
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ParseError("Invalid frontmatter format")

        # Parse YAML
        try:
            frontmatter = yaml.safe_load(parts[1])
            # Handle empty frontmatter (None from yaml.safe_load)
            if frontmatter is None:
                return {}
            if not isinstance(frontmatter, dict):
                raise ParseError("Frontmatter must be a YAML dictionary")
            return frontmatter

        except yaml.YAMLError as e:
            raise ParseError(f"Invalid YAML in frontmatter: {e}")

    except Exception as e:
        if not isinstance(e, ParseError):
            logger.error(f"Failed to parse frontmatter: {e}")
            raise ParseError(f"Failed to parse frontmatter: {e}")
        raise


def remove_frontmatter(content: str) -> str:
    """
    Remove YAML frontmatter from content.

    Args:
        content: Content with frontmatter

    Returns:
        Content with frontmatter removed

    Raises:
        ParseError: If frontmatter format is invalid
    """
    try:
        if not has_frontmatter(content):
            return content.strip()

        # Split on first two occurrences of ---
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ParseError("Invalid frontmatter format")

        return parts[2].strip()

    except Exception as e:
        if not isinstance(e, ParseError):
            logger.error(f"Failed to remove frontmatter: {e}")
            raise ParseError(f"Failed to remove frontmatter: {e}")
        raise


def remove_frontmatter_lenient(content: str) -> str:
    """
    Remove frontmatter markers and anything between them without validation.
    
    This is a more permissive version of remove_frontmatter that doesn't
    try to validate the YAML content. It simply removes everything between
    the first two '---' markers if they exist.

    Args:
        content: Content that may contain frontmatter

    Returns:
        Content with any frontmatter markers and content removed
    """
    content = content.strip()
    if not content.startswith("---"):
        return content

    # Find the second marker
    rest = content[3:].strip()
    if "---" not in rest:
        return content

    # Split on the second marker and take everything after
    parts = rest.split("---", 1)
    return parts[1].strip()


async def add_frontmatter(content: str, frontmatter: Dict[str, Any]) -> str:
    """
    Add YAML frontmatter to content.
    
    Args:
        content: Main content text
        frontmatter: Key-value pairs for frontmatter
        
    Returns:
        Content with YAML frontmatter prepended
        
    Raises:
        ParseError: If YAML serialization fails
    """
    try:
        yaml_fm = yaml.dump(frontmatter, sort_keys=False)
        return f"---\n{yaml_fm}---\n\n{content.strip()}"
    except yaml.YAMLError as e:
        logger.error(f"Failed to add frontmatter: {e}")
        raise ParseError(f"Failed to add frontmatter: {e}")


async def parse_content_with_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse both frontmatter and content.

    Args:
        content: Text content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, content without frontmatter)

    Raises:
        ParseError: If parsing fails
    """
    try:
        if not has_frontmatter(content):
            return {}, content.strip()

        frontmatter = parse_frontmatter(content)
        remaining = remove_frontmatter(content)
        return frontmatter, remaining

    except Exception as e:
        if not isinstance(e, ParseError):
            logger.error(f"Failed to parse content with frontmatter: {e}")
            raise ParseError(f"Failed to parse content with frontmatter: {e}")
        raise