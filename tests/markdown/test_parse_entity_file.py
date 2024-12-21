"""Tests for the markdown entity parser."""

from pathlib import Path
from textwrap import dedent

import pytest

from basic_memory.markdown.parser import EntityParser, ParseError


def test_parse_complete_file(tmp_path):
    """Test parsing a complete entity file."""
    content = dedent("""
        ---
        type: component
        id: component/auth_service
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: authentication, security, core
        status: active
        version: 1
        ---
        
        # Auth Service
        
        Core authentication service.
        
        <!-- Some comments that should be ignored -->
        
        ## Observations
        - [design] Stateless authentication #security #architecture (JWT based)
        - [feature] Mobile client support #mobile #oauth (Required for App Store)
        - [tech] Caching layer #performance (Redis implementation)
        
        ## Relations
        - implements [[OAuth Implementation]] (Core auth flows)
        - uses [[Redis Cache]] (Token caching)
        - specified_by [[Auth API Spec]] (OpenAPI spec)
        
        ## Metadata
        owner: team-auth
        priority: high
        """)

    test_file = tmp_path / "test_entity.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    # Check frontmatter
    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "component/auth_service"
    assert "authentication" in entity.frontmatter.tags
    assert entity.frontmatter.status == "active"

    # Check content
    assert entity.content.title == "Auth Service"
    assert len(entity.content.observations) == 3
    assert len(entity.content.relations) == 3

    # Check specific observation
    obs = entity.content.observations[0]
    assert obs.category == "design"
    assert "security" in obs.tags
    assert obs.context == "JWT based"

    # Check specific relation
    rel = entity.content.relations[0]
    assert rel.type == "implements"
    assert rel.target == "OAuth Implementation"
    assert rel.context == "Core auth flows"

    # Check metadata
    assert entity.content.metadata["owner"] == "team-auth"
    assert entity.content.metadata["priority"] == "high"


def test_parse_minimal_file(tmp_path):
    """Test parsing a minimal valid entity file."""
    content = dedent("""
        ---
        type: component
        id: minimal
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
        ---
        
        # Minimal Entity
        
        ## Observations
        - [note] Basic observation #test
        
        ## Relations
        - references [[Other Entity]]
    """)

    test_file = tmp_path / "minimal.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = parser.parse_file(test_file)

    assert entity.frontmatter.type == "component"
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1


def test_parse_file_errors(tmp_path):
    """Test error handling for invalid files."""
    parser = EntityParser()

    # Missing file
    with pytest.raises(ParseError, match="does not exist"):
        parser.parse_file(Path("nonexistent.md"))

    # Invalid frontmatter
    content = dedent("""
        ---
        invalid: yaml: [
        ---
        # Title
    """)
    test_file = tmp_path / "invalid.md"
    test_file.write_text(content)
    with pytest.raises(ParseError):
        parser.parse_file(test_file)

    # Missing required frontmatter
    content = dedent("""
        ---
        type: component
        ---
        # Title
    """)
    test_file.write_text(content)
    with pytest.raises(ParseError):
        parser.parse_file(test_file)
