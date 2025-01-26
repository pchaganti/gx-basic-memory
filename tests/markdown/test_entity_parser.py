"""Tests for entity markdown parsing."""

from pathlib import Path
from textwrap import dedent

import pytest

from basic_memory.markdown.schemas import EntityMarkdown, EntityFrontmatter, Relation


@pytest.fixture
def valid_entity_content():
    """A complete, valid entity file with all features."""
    return dedent("""
        ---
        title: Auth Service
        type: component
        permalink: auth_service
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: authentication, security, core
        ---

        Core authentication service that handles user authentication.
        
        some [[Random Link]]
        another [[Random Link with Title|Titled Link]]

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
async def test_parse_complete_file(test_config, entity_parser, valid_entity_content):
    """Test parsing a complete entity file with all features."""
    test_file = test_config.home / "test_entity.md"
    test_file.write_text(valid_entity_content)

    entity = await entity_parser.parse_file(test_file)

    # Verify entity structure
    assert isinstance(entity, EntityMarkdown)
    assert isinstance(entity.frontmatter, EntityFrontmatter)
    assert isinstance(entity.content, str)

    # Check frontmatter
    assert entity.frontmatter.title == "Auth Service"
    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.permalink == "auth_service"
    assert set(entity.frontmatter.tags) == {"authentication", "security", "core"}

    # Check content
    assert "Core authentication service that handles user authentication." in entity.content

    # Check observations
    assert len(entity.observations) == 3
    obs = entity.observations[0]
    assert obs.category == "design"
    assert obs.content == "Stateless authentication"
    assert set(obs.tags or []) == {"security", "architecture"}
    assert obs.context == "JWT based"

    # Check relations
    assert len(entity.relations) == 5
    assert (
        Relation(type="implements", target="OAuth Implementation", context="Core auth flows")
        in entity.relations
    ), "missing [[OAuth Implementation]]"
    assert (
        Relation(type="uses", target="Redis Cache", context="Token caching")
        in entity.relations
    ), "missing [[Redis Cache]]"
    assert (
        Relation(type="specified_by", target="Auth API Spec", context="OpenAPI spec")
        in entity.relations
    ), "missing [[Auth API Spec]]"

    # inline links in content
    assert (
        Relation(type="links to", target="Random Link", context=None) in entity.relations
    ), "missing [[Random Link]]"
    assert (
        Relation(type="links to", target="Random Link with Title|Titled Link", context=None)
        in entity.relations
    ), "missing [[Random Link with Title|Titled Link]]"


@pytest.mark.asyncio
async def test_parse_minimal_file(test_config, entity_parser):
    """Test parsing a minimal valid entity file."""
    content = dedent("""
        ---
        type: component
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

    test_file = test_config.home / "minimal.md"
    test_file.write_text(content)

    entity = await entity_parser.parse_file(test_file)

    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.permalink is None
    assert len(entity.observations) == 1
    assert len(entity.relations) == 1


@pytest.mark.asyncio
async def test_error_handling(test_config, entity_parser):
    """Test error handling."""

    # Missing file
    with pytest.raises(FileNotFoundError):
        await entity_parser.parse_file(Path("nonexistent.md"))

    # Invalid file encoding
    test_file = test_config.home / "binary.md"
    with open(test_file, "wb") as f:
        f.write(b"\x80\x81")  # Invalid UTF-8
    with pytest.raises(UnicodeDecodeError):
        await entity_parser.parse_file(test_file)
