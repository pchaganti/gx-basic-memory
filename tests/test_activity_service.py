"""Test activity service."""

from datetime import datetime, timedelta, timezone

import pytest

from basic_memory.services.document_service import DocumentService


async def create_test_document(
    service: DocumentService, name: str, created_delta: timedelta, updated_delta: timedelta
):
    """Helper to create document with specific timestamps."""
    now = datetime.now(timezone.utc)
    doc = await service.create_document(
        path_id=f"test/{name}.md",
        content=f"Content for {name}",
        metadata={
            "created": (now - created_delta).isoformat(),
            "updated": (now - updated_delta).isoformat(),
        },
    )
    return doc


@pytest.mark.asyncio
async def test_get_recent_activity_all_types(activity_service, document_service):
    """Test getting recent activity for all types."""
    # Create test documents with various timestamps
    test_docs = [
        await create_test_document(
            document_service, "doc1", timedelta(hours=2), timedelta(hours=2)
        ),
        await create_test_document(document_service, "doc2", timedelta(days=2), timedelta(hours=1)),
        await create_test_document(
            document_service,
            "doc3",
            timedelta(days=3),
            timedelta(days=3),  # This one should be too old
        ),
    ]

    # Get activity from last day
    result = await activity_service.get_recent_activity(timeframe="1d")

    # Verify results
    assert len(result.changes) == 2  # Should only find 2 recent docs
    assert result.summary.document_changes == 2

    # Verify changes are sorted by timestamp (most recent first)
    timestamps = [change.timestamp for change in result.changes]
    assert timestamps == sorted(timestamps, reverse=True)

    # Check specific document paths
    paths = {change.path_id for change in result.changes}
    assert "test/doc1.md" in paths
    assert "test/doc2.md" in paths
    assert "test/doc3.md" not in paths  # Too old to be included


@pytest.mark.asyncio
async def test_get_recent_activity_filtered_types(activity_service, document_service):
    """Test getting recent activity with type filtering."""
    # Create some test documents
    await create_test_document(
        document_service, "filtered_doc", timedelta(hours=1), timedelta(hours=1)
    )

    # Get activity filtered to only documents
    result = await activity_service.get_recent_activity(timeframe="1d", activity_types=["document"])

    # Verify results
    assert len(result.changes) == 1
    assert result.summary.document_changes == 1
    assert result.summary.entity_changes == 0
    assert result.changes[0].activity_type == "document"


@pytest.mark.asyncio
async def test_get_recent_activity_without_content(activity_service, document_service):
    """Test getting activity without content."""
    # Create test document
    await create_test_document(
        document_service, "no_content_doc", timedelta(hours=1), timedelta(hours=1)
    )

    # Get activity without content
    result = await activity_service.get_recent_activity(timeframe="1d", include_content=False)

    # Verify results
    assert len(result.changes) == 1
    assert result.changes[0].content is None


@pytest.mark.asyncio
async def test_change_type_detection(activity_service, document_service):
    """Test correct detection of created vs updated changes."""
    now = datetime.now(timezone.utc)

    # Create documents with different creation/update patterns
    new_doc = await create_test_document(
        document_service,
        "new_doc",
        timedelta(hours=1),  # Created recently
        timedelta(hours=1),  # Updated recently
    )

    updated_doc = await create_test_document(
        document_service,
        "updated_doc",
        timedelta(days=2),  # Created a while ago
        timedelta(hours=2),  # But updated recently
    )

    # Get activity
    result = await activity_service.get_recent_activity(timeframe="1d")

    # Verify change types
    changes_by_path = {change.path_id: change for change in result.changes}

    assert changes_by_path["test/new_doc.md"].change_type == "created"
    assert changes_by_path["test/updated_doc.md"].change_type == "updated"
