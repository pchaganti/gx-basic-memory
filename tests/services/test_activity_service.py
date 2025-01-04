"""Test activity service."""
import os.path
from datetime import datetime, timedelta, timezone
import tempfile
from pathlib import Path

import pytest

from basic_memory.services.activity_service import ActivityService
from basic_memory.services.document_service import DocumentService
from basic_memory.services.entity_service import EntityService
from basic_memory.services.relation_service import RelationService
from basic_memory.repository.document_repository import DocumentRepository
from basic_memory.repository.entity_repository import EntityRepository
from basic_memory.repository.relation_repository import RelationRepository


@pytest.fixture
def test_dir():
    """Create a temporary test directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = os.path.join(tmpdir, 'documents')
        os.makedirs(docs_dir)
        yield Path(tmpdir)





@pytest.fixture
def activity_service(document_service, entity_service, relation_service):
    """Create activity service with real dependencies."""
    return ActivityService(entity_service, document_service, relation_service)


async def create_test_document(service: DocumentService, name: str, content: str = "") -> str:
    """Create a test document."""
    path_id = f"test/{name}.md"
    doc_content = content or f"Content for {name}"
    return await service.create_document(path_id, doc_content)


@pytest.mark.asyncio
async def test_get_recent_activity_all_types(activity_service, document_service):
    """Test finding recently created documents."""
    # Create test documents
    doc1 = await create_test_document(document_service, "doc1")
    doc2 = await create_test_document(document_service, "doc2")

    # Get activity from last day
    result = await activity_service.get_recent_activity(timeframe="1d")

    # Should find both docs
    assert len(result.changes) == 2
    assert result.summary.document_changes == 2
    assert result.summary.entity_changes == 0
    assert result.summary.relation_changes == 0

    # Changes should be sorted by timestamp (most recent first)
    timestamps = [change.timestamp for change in result.changes]
    assert timestamps == sorted(timestamps, reverse=True)

    paths = {change.path_id for change in result.changes}
    assert "test/doc1.md" in paths
    assert "test/doc2.md" in paths


@pytest.mark.asyncio
async def test_get_recent_activity_filtered_types(activity_service, document_service):
    """Test activity filtering by type."""
    # Create test document
    await create_test_document(document_service, "filtered_doc")

    # Get activity filtered to only documents
    result = await activity_service.get_recent_activity(
        timeframe="1d",
        activity_types=["document"]
    )

    # Should find our test doc
    assert len(result.changes) == 1
    assert result.summary.document_changes == 1
    assert result.summary.entity_changes == 0
    assert result.changes[0].activity_type == "document"
