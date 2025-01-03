"""Test sync service."""

from pathlib import Path
import pytest
import pytest_asyncio

from basic_memory.config import ProjectConfig
from basic_memory.services import DocumentService, EntityService, FileChangeScanner
from basic_memory.services.sync.knowledge_sync_service import KnowledgeSyncService
from basic_memory.services.sync.sync_service import SyncService
from basic_memory.markdown import KnowledgeParser, EntityMarkdown
from basic_memory.models import Document, Entity, Observation


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_empty_directories(sync_service: SyncService, test_config: ProjectConfig):
    """Test syncing empty directories."""
    await sync_service.sync(test_config.home)
    
    # Should not raise exceptions for empty dirs
    assert (test_config.documents_dir).exists()
    assert (test_config.knowledge_dir).exists()
  

@pytest.mark.asyncio
async def test_sync_deletes(
    sync_service: SyncService,
    test_config: ProjectConfig,
    document_service: DocumentService,
    entity_service: EntityService
):
    """Test sync handles deletions."""
    # Add records to DB that don't exist in filesystem
    doc = Document(
        path_id="deleted.md",
        file_path="deleted.md",
        checksum="12345678"
    )
    await document_service.repository.add(doc)
    
    entity = Entity(
        path_id="concept/deleted",
        name="Deleted",
        entity_type="concept",
        file_path="concept/deleted.md",
        checksum = "12345678"
    )
    await entity_service.repository.add(entity)
    
    # Run sync
    await sync_service.sync(test_config.home)
    
    # Verify deletions
    docs = await document_service.repository.find_all()
    assert len(docs) == 0
        
    entities = await entity_service.repository.find_all()
    assert len(entities) == 0