"""Tests for MemoryUrl parsing."""

import pytest
from pydantic import ValidationError
from basic_memory.schemas.memory_url import MemoryUrl


def test_basic_permalink():
    """Test basic permalink parsing."""
    url = MemoryUrl.parse("memory://basic-memory/specs/search")
    assert url.scheme == "memory"
    assert url.host == "basic-memory"
    assert url.path == "/specs/search"
    assert url.pattern is None
    assert url.fuzzy is None
    assert url.params == {}


def test_glob_pattern():
    """Test glob pattern conversion."""
    url = MemoryUrl.parse("memory://basic-memory/specs/search/*")
    assert url.host == "basic-memory"
    assert url.path == "/specs/search/*"
    assert url.pattern == "specs/search/%"
    assert url.fuzzy is None


def test_fuzzy_search():
    """Test fuzzy search term parsing."""
    url = MemoryUrl.parse("memory://basic-memory/topic/search~ranking")
    assert url.host == "basic-memory"
    assert url.path == "/topic/search~ranking"
    assert url.pattern is None
    assert url.fuzzy == "topic/search ranking"


def test_related_prefix():
    """Test related content prefix."""
    url = MemoryUrl.parse("memory://basic-memory/related/specs/search")
    assert url.host == "basic-memory"
    assert url.path == "/related/specs/search"
    assert url.params == {
        "type": "related",
        "target": "specs/search"
    }


def test_context_prefix():
    """Test context prefix."""
    url = MemoryUrl.parse("memory://basic-memory/context/current")
    assert url.host == "basic-memory"
    assert url.path == "/context/current"
    assert url.params == {
        "type": "context",
        "target": "current"
    }


def test_invalid_scheme():
    """Test that other schemes are rejected."""
    with pytest.raises(ValidationError):
        MemoryUrl.parse("http://basic-memory/specs/search")


def test_missing_host():
    """Test that host is required."""
    with pytest.raises(ValidationError):
        MemoryUrl.parse("memory:///specs/search")


def test_complex_pattern():
    """Test multiple glob patterns."""
    url = MemoryUrl.parse("memory://basic-memory/specs/*/search/*")
    assert url.host == "basic-memory"
    assert url.path == "/specs/*/search/*"
    assert url.pattern == "specs/%/search/%"


def test_complex_fuzzy():
    """Test multiple fuzzy terms."""
    url = MemoryUrl.parse("memory://basic-memory/specs/search~ranking~performance")
    assert url.host == "basic-memory"
    assert url.path == "/specs/search~ranking~performance"
    assert url.fuzzy == "specs/search ranking performance"


def test_url_reconstruction():
    """Test converting back to string."""
    original = "memory://basic-memory/specs/search"
    url = MemoryUrl.parse(original)
    assert str(url) == original


def test_relative_path():
    """Test getting path without leading slash."""
    url = MemoryUrl.parse("memory://basic-memory/specs/search")
    assert url.relative_path() == "specs/search"


def test_project_property():
    """Test project name access."""
    url = MemoryUrl.parse("memory://basic-memory/specs/search")
    assert url.project == "basic-memory"