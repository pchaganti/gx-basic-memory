"""Test sync service."""

from pathlib import Path
import pytest

from basic_memory.config import ProjectConfig
from basic_memory.services import DocumentService
from basic_memory.services.sync.sync_service import SyncService
from basic_memory.models import Document


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_documents(
    sync_service: SyncService, test_config: ProjectConfig, document_service: DocumentService
):
    """Test syncing document files."""
    # Create test files
    docs_dir = test_config.documents_dir
    await create_test_file(docs_dir / "new.md", "new document")
    await create_test_file(docs_dir / "modified.md", "modified document")

    # Add existing doc to DB
    doc = Document(path_id="modified.md", file_path="modified.md", checksum="12345678")
    added = await document_service.repository.add(doc)

    # Run sync
    await sync_service.sync(test_config.home)

    # Verify results
    documents = await document_service.repository.find_all()
    assert len(documents) == 2

    paths = {d.path_id for d in documents}
    assert "new.md" in paths
    assert "modified.md" in paths
