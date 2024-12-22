"""Tests for entity file parsing."""

from textwrap import dedent

import pytest

from basic_memory.markdown.parser import EntityParser


@pytest.mark.asyncio
async def test_parse_complete_file(tmp_path):
    """Test parsing a complete entity file."""
    content = dedent("""
        ---
        type: component
        id: 123
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: authentication, security, core
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

        ---
        owner: team-auth
        priority: high
        ---
        """)

    test_file = tmp_path / "test_entity.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = await parser.parse_file(test_file)

    # Check frontmatter
    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "123"
    assert "authentication" in entity.frontmatter.tags

    # Check content
    assert entity.content.title == "Auth Service"
    assert len(entity.content.observations) == 3
    assert len(entity.content.relations) == 3

    # Check specific observation
    obs = entity.content.observations[0]
    assert obs.category == "design"
    assert "security" in obs.tags  # pyright: ignore [reportOperatorIssue]
    assert obs.context == "JWT based"

    # Check specific relation
    rel = entity.content.relations[0]
    assert rel.type == "implements"
    assert rel.target == "OAuth Implementation"
    assert rel.context == "Core auth flows"

    # Check metadata
    assert entity.metadata.metadata["owner"] == "team-auth"
    assert entity.metadata.metadata["priority"] == "high"


@pytest.mark.asyncio
async def test_parse_minimal_file(tmp_path):
    """Test parsing a minimal valid entity file."""
    content = dedent("""
        ---
        type: component
        id: 0
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: 
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
    entity = await parser.parse_file(test_file)

    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "0"
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1
    assert not entity.metadata.metadata  # Empty metadata


@pytest.mark.asyncio
async def test_file_with_metadata_only(tmp_path):
    """Test parsing a file that has metadata but no content."""
    content = dedent("""
        ---
        type: component
        id: minimal
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
        ---

        # Empty Entity

        ---
        owner: test-team
        status: active
        ---
        """)

    test_file = tmp_path / "metadata_only.md"
    test_file.write_text(content)

    parser = EntityParser()
    entity = await parser.parse_file(test_file)

    assert entity.metadata.metadata["owner"] == "test-team"
    assert entity.metadata.metadata["status"] == "active"
    assert not entity.content.observations
    assert not entity.content.relations
