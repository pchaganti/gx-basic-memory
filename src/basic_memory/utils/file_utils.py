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
        temp_path.replace(path)
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        logger.error(f"Failed to write file: {path}: {e}")
        raise FileWriteError(f"Failed to write file {path}: {e}")


async def add_frontmatter(content: str, metadata: Dict[str, Any]) -> str:
    """
    Add YAML frontmatter to content.
    
    Args:
        content: Main content text
        metadata: Key-value pairs for frontmatter
        
    Returns:
        Content with YAML frontmatter prepended
        
    Raises:
        ParseError: If YAML serialization fails
    """
    try:
        yaml_fm = yaml.dump(metadata, sort_keys=False)
        return f"---\n{yaml_fm}---\n\n{content}"
    except yaml.YAMLError as e:
        logger.error(f"Failed to add frontmatter: {e}")
        raise ParseError(f"Failed to add frontmatter: {e}")


async def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from content.
    
    Args:
        content: Text content with optional frontmatter
        
    Returns:
        Tuple of (frontmatter dict, remaining content)
        
    Raises:
        ParseError: If frontmatter parsing fails
    """
    try:
        if not content.startswith("---\n"):
            return {}, content
            
        try:
            _, fm, content = content.split("---\n", 2)
        except ValueError as e:
            raise ParseError("Invalid frontmatter format") from e
            
        try:
            metadata = yaml.safe_load(fm)
            return metadata or {}, content.strip()
        except yaml.YAMLError as e:
            raise ParseError(f"Invalid YAML in frontmatter: {e}") from e
            
    except Exception as e:
        if not isinstance(e, ParseError):
            logger.error(f"Failed to parse frontmatter: {e}")
            raise ParseError(f"Failed to parse frontmatter: {e}") from e
        raise