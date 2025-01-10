"""Tests for entity markdown parsing."""

from pathlib import Path
from textwrap import dedent

import pytest

from basic_memory.markdown.entity_parser import EntityParser
from basic_memory.markdown.schemas import EntityMarkdown, EntityFrontmatter, EntityContent
from basic_memory.utils.file_utils import ParseError, FileError


@pytest.fixture
def valid_entity_content():
    """A complete, valid entity file with all features."""
    return dedent("""
        ---
        title: Auth Service
        type: component
        id: auth_service
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: authentication, security, core
        ---

        Core authentication service that handles user authentication.

        ## Observations
        - [design] Stateless authentication #security #architecture (JWT based)
        - [feature] Mobile client support #mobile #oauth (Required for App Store)
        - [tech] Caching layer #performance (Redis implementation)

        ## Relations
        - implements [[OAuth Implementation]] (Core auth flows)
        - uses [[Redis Cache]] (Token caching)
        - specified_by [[Auth API Spec]] (OpenAPI spec)
        """)


@pytest.mark.asyncio
async def test_parse_complete_file(test_config, valid_entity_content):
    """Test parsing a complete entity file with all features."""
    test_file = test_config.home / "test_entity.md"
    test_file.write_text(valid_entity_content)

    parser = EntityParser(test_config.home)
    entity = await parser.parse_file(test_file)

    # Verify entity structure
    assert isinstance(entity, EntityMarkdown)
    assert isinstance(entity.frontmatter, EntityFrontmatter)
    assert isinstance(entity.content, EntityContent)

    # Check frontmatter
    assert entity.frontmatter.title == "Auth Service"
    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "auth_service"
    assert set(entity.frontmatter.tags) == {"authentication", "security", "core"}

    # Check content
    assert "Core authentication service that handles user authentication." in entity.content.content

    # Check observations
    assert len(entity.content.observations) == 3
    obs = entity.content.observations[0]
    assert obs.category == "design"
    assert obs.content == "Stateless authentication"
    assert set(obs.tags or []) == {"security", "architecture"}
    assert obs.context == "JWT based"

    # Check relations
    assert len(entity.content.relations) == 3
    rel = entity.content.relations[0]
    assert rel.type == "implements"
    assert rel.target == "OAuth Implementation"
    assert rel.context == "Core auth flows"


@pytest.mark.asyncio
async def test_parse_minimal_file(tmp_path):
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

    parser = EntityParser(tmp_path)
    entity = await parser.parse_file(test_file)

    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "minimal"
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1




@pytest.mark.asyncio
async def test_error_handling(tmp_path):
    """Test error handling."""
    parser = EntityParser(tmp_path)

    # Missing file
    with pytest.raises(FileNotFoundError):
        await parser.parse_file(Path("nonexistent.md"))

    # Invalid file encoding
    test_file = tmp_path / "binary.md"
    with open(test_file, "wb") as f:
        f.write(b"\x80\x81")  # Invalid UTF-8
    with pytest.raises(UnicodeDecodeError):
        await parser.parse_file(test_file)
