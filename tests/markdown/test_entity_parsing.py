"""Tests for entity markdown parsing."""

from pathlib import Path
from textwrap import dedent

import pytest

from basic_memory.markdown.knowledge_parser import KnowledgeParser
from basic_memory.markdown.schemas import EntityMarkdown, EntityFrontmatter, EntityContent
from basic_memory.utils.file_utils import ParseError, FileError


@pytest.fixture
def valid_entity_content():
    """A complete, valid entity file with all features."""
    return dedent("""
        ---
        type: component
        id: auth_service
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: authentication, security, core
        ---

        # Auth Service

        Core authentication service that handles user authentication.

        ## Observations
        - [design] Stateless authentication #security #architecture (JWT based)
        - [feature] Mobile client support #mobile #oauth (Required for App Store)
        - [tech] Caching layer #performance (Redis implementation)

        ## Relations
        - implements [[OAuth Implementation]] (Core auth flows)
        - uses [[Redis Cache]] (Token caching)
        - specified_by [[Auth API Spec]] (OpenAPI spec)

        # Metadata
        <!-- anything below this line is for AI -->

        ```yml
        owner: team-auth
        priority: high
        ```
        """)


@pytest.mark.asyncio
async def test_parse_complete_file(tmp_path, valid_entity_content):
    """Test parsing a complete entity file with all features."""
    test_file = tmp_path / "test_entity.md"
    test_file.write_text(valid_entity_content)

    parser = KnowledgeParser()
    entity = await parser.parse_file(test_file)

    # Verify entity structure
    assert isinstance(entity, EntityMarkdown)
    assert isinstance(entity.frontmatter, EntityFrontmatter)
    assert isinstance(entity.content, EntityContent)

    # Check frontmatter
    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "auth_service"
    assert set(entity.frontmatter.tags) == {"authentication", "security", "core"}

    # Check content
    assert entity.content.title == "Auth Service"
    assert (
        entity.content.description
        == "Core authentication service that handles user authentication."
    )

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

    # Check metadata
    assert entity.entity_metadata.data["owner"] == "team-auth"


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

    parser = KnowledgeParser()
    entity = await parser.parse_file(test_file)

    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "minimal"
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1
    assert not entity.entity_metadata.data  # Empty metadata


@pytest.mark.asyncio
async def test_parse_content_str(valid_entity_content):
    """Test parsing content string directly."""
    parser = KnowledgeParser()
    entity = await parser.parse_content_str(valid_entity_content)

    assert isinstance(entity, EntityMarkdown)
    assert entity.frontmatter.type == "component"
    assert entity.content.title == "Auth Service"
    assert len(entity.content.observations) == 3
    assert len(entity.content.relations) == 3


@pytest.mark.asyncio
async def test_metadata_handling(tmp_path):
    """Test metadata section parsing."""
    parser = KnowledgeParser()

    # Multiple metadata fields
    content = dedent("""
        ---
        type: component
        id: test
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
        ---
        # Test Entity
        ## Observations
        - [test] Test

        # Metadata
        <!-- anything below this line is for AI -->

        ```yml
        owner: test-team
        priority: high
        nested:
          key: value
          list: [1, 2, 3]
        ```
        """)
    test_file = tmp_path / "metadata.md"
    test_file.write_text(content)

    entity = await parser.parse_file(test_file)
    assert entity.entity_metadata.data["owner"] == "test-team"
    assert entity.entity_metadata.data["priority"] == "high"
    assert entity.entity_metadata.data["nested"]["key"] == "value"
    assert entity.entity_metadata.data["nested"]["list"] == [1, 2, 3]

    # No metadata section
    content = dedent("""
        ---
        type: component
        id: test
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
        ---
        # Test Entity
        ## Observations
        - [test] Test
        """)
    test_file = tmp_path / "no_metadata.md"
    test_file.write_text(content)

    entity = await parser.parse_file(test_file)
    assert entity.entity_metadata.data == {}


@pytest.mark.asyncio
async def test_error_handling(tmp_path):
    """Test error handling."""
    parser = KnowledgeParser()

    # Missing file
    with pytest.raises(FileError):
        await parser.parse_file(Path("nonexistent.md"))

    # Invalid file encoding
    test_file = tmp_path / "binary.md"
    with open(test_file, "wb") as f:
        f.write(b"\x80\x81")  # Invalid UTF-8
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)

    # No frontmatter section
    content = "# Just a title\nNo frontmatter"
    test_file = tmp_path / "no_frontmatter.md"
    test_file.write_text(content)
    with pytest.raises(ParseError):
        await parser.parse_file(test_file)
