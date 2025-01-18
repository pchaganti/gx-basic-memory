"""Tests for MemoryUrl parsing."""

import pytest
from pydantic import ValidationError

from basic_memory.config import config
from basic_memory.schemas.memory import MemoryUrl


def test_basic_permalink():
    """Test basic permalink parsing."""
    url = MemoryUrl.validate(f"memory://{config.project}/specs/search")
    assert url.scheme == "memory"
    assert url.host == config.project
    assert url.path == "/specs/search"


def test_glob_pattern():
    """Test pattern matching."""
    url = MemoryUrl.validate(f"memory://{config.project}/specs/search/*")
    assert url.host == config.project
    assert url.path == "/specs/search/*"


def test_related_prefix():
    """Test related content prefix."""
    url = MemoryUrl.validate(f"memory://{config.project}/related/specs/search")
    assert url.host == config.project
    assert url.path == "/related/specs/search"


def test_context_prefix():
    """Test context prefix."""
    url = MemoryUrl.validate(f"memory://{config.project}/context/current")
    assert url.host == config.project
    assert url.path == "/context/current"



def test_complex_pattern():
    """Test multiple glob patterns."""
    url = MemoryUrl.validate(f"memory://{config.project}/specs/*/search/*")
    assert url.host == config.project
    assert url.path == "/specs/*/search/*"


def test_path_with_no_host():
    """Test getting path without leading slash."""
    url = MemoryUrl.validate("memory://specs/search")
    assert url.relative_path() == "specs/search"

