"""Tests for KnowledgeWriter."""

from datetime import datetime, UTC

import pytest
from basic_memory.models import Entity, Observation, Relation
from basic_memory.markdown.knowledge_writer import KnowledgeWriter
from basic_memory.models.knowledge import EntityType


@pytest.fixture
def knowledge_writer() -> KnowledgeWriter:
    return KnowledgeWriter()


@pytest.fixture
def sample_entity() -> Entity:
    """Create a sample knowledge entity for testing."""
    return Entity(
        id=1,
        name="test_entity",
        entity_type=EntityType.KNOWLEDGE,
        path_id="knowledge/test_entity",
        file_path="knowledge/test_entity.md",
        description="Test description",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 2, tzinfo=UTC)
    )


@pytest.fixture
def entity_with_observations(sample_entity: Entity) -> Entity:
    """Create an entity with observations."""
    sample_entity.observations = [
        Observation(entity_id=1, category="tech", content="First observation"),
        Observation(entity_id=1, category="design", content="Second observation", context="Some context")
    ]
    return sample_entity


@pytest.fixture
def entity_with_relations(sample_entity: Entity) -> Entity:
    """Create an entity with relations."""
    target = Entity(
        id=2,
        name="target_entity",
        entity_type=EntityType.KNOWLEDGE,
        path_id="knowledge/target_entity"
    )
    sample_entity.outgoing_relations = [
        Relation(
            from_id=1,
            to_id=2,
            relation_type="connects_to",
            to_entity=target
        )
    ]
    return sample_entity


@pytest.mark.asyncio
async def test_format_frontmatter_basic(knowledge_writer: KnowledgeWriter, sample_entity: Entity):
    """Test basic frontmatter formatting."""
    frontmatter = await knowledge_writer.format_frontmatter(sample_entity)
    
    assert frontmatter["id"] == "knowledge/test_entity"
    assert frontmatter["type"] == EntityType.KNOWLEDGE
    assert frontmatter["created"] == "2025-01-01T00:00:00+00:00"
    assert frontmatter["modified"] == "2025-01-02T00:00:00+00:00"


@pytest.mark.asyncio
async def test_format_frontmatter_with_metadata(knowledge_writer: KnowledgeWriter, sample_entity: Entity):
    """Test frontmatter includes entity metadata."""
    sample_entity.entity_metadata = {
        "status": "active",
        "priority": "high"
    }
    
    frontmatter = await knowledge_writer.format_frontmatter(sample_entity)
    
    assert frontmatter["status"] == "active"
    assert frontmatter["priority"] == "high"
    assert frontmatter["id"] == "knowledge/test_entity"


@pytest.mark.asyncio
async def test_format_content_basic(knowledge_writer: KnowledgeWriter, sample_entity: Entity):
    """Test basic content formatting."""
    content = ""
    result = await knowledge_writer.format_content(sample_entity, content)
    
    assert "# test_entity" in result
    assert "Test description" in result


@pytest.mark.asyncio
async def test_format_content_with_observations(
    knowledge_writer: KnowledgeWriter,
    entity_with_observations: Entity
):
    """Test content formatting with observations."""
    content = ""
    result = await knowledge_writer.format_content(entity_with_observations, content)
    
    assert "## Observations" in result
    assert "- [tech] First observation" in result
    assert "- [design] Second observation (Some context)" in result


@pytest.mark.asyncio
async def test_format_content_with_relations(
    knowledge_writer: KnowledgeWriter,
    entity_with_relations: Entity
):
    """Test content formatting with relations."""
    content = ""
    result = await knowledge_writer.format_content(entity_with_relations, content)
    
    assert "## Relations" in result
    assert "- connects_to [[target_entity]]" in result


@pytest.mark.asyncio
async def test_format_content_full_entity(
    knowledge_writer: KnowledgeWriter,
    entity_with_relations: Entity,
    entity_with_observations: Entity
):
    """Test content formatting with all entity features."""
    # Combine observations and relations
    entity_with_relations.observations = entity_with_observations.observations
    content = ""
    result = await knowledge_writer.format_content(entity_with_relations, content)
    
    # Verify all sections present
    assert "# test_entity" in result
    assert "Test description" in result
    assert "## Observations" in result
    assert "- [tech] First observation" in result
    assert "## Relations" in result
    assert "- connects_to [[target_entity]]" in result