"""Tests for MemoryUrl parsing."""

import pytest
from basic_memory.schemas.memory import MemoryUrl


def test_basic_permalink():
    """Test basic permalink parsing."""
    url = MemoryUrl.validate("memory://specs/search")
    assert str(url) == "memory://specs/search"
    assert url.path == "specs/search"


def test_glob_pattern():
    """Test pattern matching."""
    url = MemoryUrl.validate("memory://specs/search/*")
    assert url.path == "specs/search/*"


def test_related_prefix():
    """Test related content prefix."""
    url = MemoryUrl.validate("memory://related/specs/search")
    assert url.path == "related/specs/search"


def test_context_prefix():
    """Test context prefix."""
    url = MemoryUrl.validate("memory://context/current")
    assert url.path == "context/current"


def test_complex_pattern():
    """Test multiple glob patterns."""
    url = MemoryUrl.validate("memory://specs/*/search/*")
    assert url.path == "specs/*/search/*"


def test_path_with_dashes():
    """Test path with dashes and other chars."""
    url = MemoryUrl.validate("memory://file-sync-and-note-updates-implementation")
    assert url.path == "file-sync-and-note-updates-implementation"
    

def test_invalid_url():
    """Test URL must start with memory://."""
    with pytest.raises(ValueError, match="Invalid memory URL"):
        MemoryUrl.validate("http://specs/search")
        

def test_str_representation():
    """Test converting back to string."""
    url = MemoryUrl.validate("memory://specs/search")
    assert str(url) == "memory://specs/search"