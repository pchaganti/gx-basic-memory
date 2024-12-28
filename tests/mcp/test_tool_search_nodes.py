"""Tests for search_nodes MCP tool."""

import pytest

from basic_memory.mcp.tools.search import search_nodes
from basic_memory.mcp.tools.knowledge import create_entities
from basic_memory.schemas.base import Entity, ObservationCategory
from basic_memory.schemas.request import CreateEntityRequest, SearchNodesRequest, ObservationCreate


@pytest.mark.asyncio
async def test_basic_search(client):
    """Test basic text search."""
    # Create some test entities
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                name="SearchComponent", 
                entity_type="component",
                description="A searchable component",
                observations=["This has some searchable text"]
            ),
            Entity(
                name="OtherComponent",
                entity_type="component",
                description="Another component",
                observations=["This is unrelated"]
            )
        ]
    )
    await create_entities(entity_request)

    # Search for "searchable"
    request = SearchNodesRequest(query="searchable")
    result = await search_nodes(request)

    # Should find one matching entity
    assert len(result.matches) == 1
    assert result.matches[0].name == "SearchComponent"
    assert result.query == "searchable"


@pytest.mark.asyncio
async def test_search_with_category(client):
    """Test search with category filter."""
    # Create an entity with different observation categories
    obs_tech = ObservationCreate(
        content="Technical detail about implementation",
        category=ObservationCategory.TECH
    )
    obs_design = ObservationCreate(
        content="Design decision about architecture",
        category=ObservationCategory.DESIGN
    )
    
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                name="TestEntity",
                entity_type="test",
                description="Test entity",
                observations=[obs_tech.content, obs_design.content]
            )
        ]
    )
    await create_entities(entity_request)

    # Search for tech observations only
    request = SearchNodesRequest(
        query="implementation",
        category=ObservationCategory.TECH
    )
    tech_result = await search_nodes(request)
    assert len(tech_result.matches) == 1

    # Search for design observations only
    request = SearchNodesRequest(
        query="architecture",
        category=ObservationCategory.DESIGN
    )
    design_result = await search_nodes(request)
    assert len(design_result.matches) == 1


@pytest.mark.asyncio
async def test_search_multiple_matches(client):
    """Test search returning multiple entities."""
    # Create multiple entities with similar content
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                name="Component1",
                entity_type="component",
                description="Uses SQLite database",
                observations=["Implements SQLite storage"]
            ),
            Entity(
                name="Component2",
                entity_type="component",
                description="Another SQLite component",
                observations=["Also uses SQLite"]
            )
        ]
    )
    await create_entities(entity_request)

    # Search for SQLite
    request = SearchNodesRequest(query="SQLite")
    result = await search_nodes(request)

    # Should find both entities
    assert len(result.matches) == 2
    names = {e.name for e in result.matches}
    assert "Component1" in names
    assert "Component2" in names


@pytest.mark.asyncio
async def test_search_no_matches(client):
    """Test search with no matching results."""
    # Create an entity with unrelated content
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                name="UnrelatedEntity",
                entity_type="test",
                description="Something unrelated",
                observations=["Nothing to see here"]
            )
        ]
    )
    await create_entities(entity_request)

    # Search for non-matching term
    request = SearchNodesRequest(query="nonexistent")
    result = await search_nodes(request)

    # Should find no matches
    assert len(result.matches) == 0
    assert result.query == "nonexistent"


@pytest.mark.asyncio
async def test_search_case_insensitive(client):
    """Test that search is case insensitive."""
    # Create entity with mixed case text
    entity_request = CreateEntityRequest(
        entities=[
            Entity(
                name="MixedCase",
                entity_type="test",
                description="Testing MIXED case text",
                observations=["Some MiXeD cAsE content"]
            )
        ]
    )
    await create_entities(entity_request)

    # Search with different cases
    lower_request = SearchNodesRequest(query="mixed")
    upper_request = SearchNodesRequest(query="MIXED")
    mixed_request = SearchNodesRequest(query="MiXeD")

    # All should find the entity
    lower_result = await search_nodes(lower_request)
    upper_result = await search_nodes(upper_request)
    mixed_result = await search_nodes(mixed_request)

    assert len(lower_result.matches) == 1
    assert len(upper_result.matches) == 1
    assert len(mixed_result.matches) == 1
    assert all(r.matches[0].name == "MixedCase" 
              for r in [lower_result, upper_result, mixed_result])