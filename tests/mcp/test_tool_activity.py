"""Tests for activity tracking MCP tool."""

import pytest

from basic_memory.mcp.tools.documents import create_document
from basic_memory.mcp.tools.knowledge import create_entities
from basic_memory.mcp.tools.activity import get_recent_activity
from basic_memory.schemas.base import Entity
from basic_memory.schemas.request import CreateEntityRequest, DocumentRequest
from basic_memory.schemas.activity import ActivityType


@pytest.mark.asyncio
async def test_get_recent_activity_basic(client):
    """Test getting activity after creating some documents."""
    # Create test documents
    doc1 = await create_document(
        DocumentRequest(
            path_id="test/doc1.md",
            content="Test document 1",
            doc_metadata={}
        )
    )
    doc2 = await create_document(
        DocumentRequest(
            path_id="test/doc2.md",
            content="Test document 2",
            doc_metadata={}
        )
    )

    # Get recent activity
    result = await get_recent_activity()

    # Should find both documents
    assert len(result.changes) == 2
    assert result.summary.document_changes == 2
    assert result.summary.entity_changes == 0
    assert result.summary.relation_changes == 0

    # Should be sorted by timestamp
    timestamps = [change.timestamp for change in result.changes]
    assert timestamps == sorted(timestamps, reverse=True)

    # Should have both documents
    paths = {change.path_id for change in result.changes}
    assert "test/doc1.md" in paths
    assert "test/doc2.md" in paths


@pytest.mark.asyncio
async def test_get_recent_activity_filtered(client):
    """Test activity filtering by type."""
    # Create both document and entity changes
    doc = await create_document(
        DocumentRequest(
            path_id="test/filtered_doc.md",
            content="Test document",
            doc_metadata={}
        )
    )
    
    entity_request = CreateEntityRequest(
        entities=[Entity(name="TestEntity", entity_type="test")]
    )
    entity = await create_entities(entity_request)

    # Get only document changes
    result = await get_recent_activity(
        timeframe="1d",
        activity_types=[ActivityType.DOCUMENT]  # Use enum directly
    )

    # Should only find document changes
    assert len(result.changes) == 1
    assert result.summary.document_changes == 1
    assert result.summary.entity_changes == 0
    assert result.changes[0].activity_type == ActivityType.DOCUMENT
    assert result.changes[0].path_id == "test/filtered_doc.md"


@pytest.mark.asyncio
async def test_get_recent_activity_content_handling(client):
    """Test content handling for different activity types."""
    # Create document and entity with description
    doc = await create_document(
        DocumentRequest(
            path_id="test/content_doc.md",
            content="Document content",
            doc_metadata={}
        )
    )
    
    entity_request = CreateEntityRequest(
        entities=[Entity(
            name="ContentEntity", 
            entity_type="test",
            description="Entity description"
        )]
    )
    entity = await create_entities(entity_request)

    # Get activity
    result = await get_recent_activity(timeframe="1d")

    # Find the document and entity changes
    doc_changes = [c for c in result.changes if c.activity_type == ActivityType.DOCUMENT]
    entity_changes = [c for c in result.changes if c.activity_type == ActivityType.ENTITY]
    
    # Document should have no content (lives in filesystem)
    assert len(doc_changes) == 1
    assert doc_changes[0].content is None
    
    # Entity should include description as content
    assert len(entity_changes) == 1
    assert entity_changes[0].content == "Entity description"


@pytest.mark.asyncio
async def test_get_recent_activity_multiple_types(client):
    """Test tracking activity across all types."""
    # Create changes of different types
    doc = await create_document(
        DocumentRequest(
            path_id="test/activity_doc.md",
            content="Test document",
            doc_metadata={}
        )
    )
    
    entity_request = CreateEntityRequest(
        entities=[
            Entity(name="Entity1", entity_type="test"),
            Entity(name="Entity2", entity_type="test")
        ]
    )
    entities = await create_entities(entity_request)

    # Get all activity
    result = await get_recent_activity()

    # Should find all changes
    assert result.summary.document_changes == 1
    assert result.summary.entity_changes == 2
    assert result.summary.relation_changes == 0  # No relations created

    # Changes should be the right types
    doc_changes = [c for c in result.changes if c.activity_type == ActivityType.DOCUMENT]
    entity_changes = [c for c in result.changes if c.activity_type == ActivityType.ENTITY]
    
    assert len(doc_changes) == 1
    assert len(entity_changes) == 2