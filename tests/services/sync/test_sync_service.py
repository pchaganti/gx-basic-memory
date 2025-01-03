"""Test sync service."""

from pathlib import Path
import pytest
import pytest_asyncio

from basic_memory.services import DocumentService, EntityService, FileChangeScanner
from basic_memory.services.sync.knowledge_sync_service import KnowledgeSyncService
from basic_memory.services.sync.sync_service import SyncService
from basic_memory.markdown import KnowledgeParser, EntityMarkdown
from basic_memory.models import Document, Entity, Observation


@pytest_asyncio.fixture
async def sync_service(
    document_service: DocumentService,
    knowledge_sync_service: KnowledgeSyncService,
    file_change_scanner: FileChangeScanner,
    knowledge_parser: KnowledgeParser,
) -> SyncService:
    """Create sync service for testing."""
    return SyncService(
        scanner=file_change_scanner,
        document_service=document_service,
        knowledge_sync_service=knowledge_sync_service,
        knowledge_parser=knowledge_parser,
    )


@pytest.fixture
def root_dir(tmp_path: Path) -> Path:
    """Create temp directory structure."""
    (tmp_path / "documents").mkdir()
    (tmp_path / "knowledge").mkdir()
    return tmp_path


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_sync_empty_directories(sync_service: SyncService, root_dir: Path):
    """Test syncing empty directories."""
    await sync_service.sync(root_dir)
    
    # Should not raise exceptions for empty dirs
    assert (root_dir / "documents").exists()
    assert (root_dir / "knowledge").exists()


@pytest.mark.asyncio
async def test_sync_documents(
    sync_service: SyncService,
    root_dir: Path,
    document_service: DocumentService
):
    """Test syncing document files."""
    # Create test files
    docs_dir = root_dir / "documents"
    await create_test_file(docs_dir / "new.md", "new document")
    await create_test_file(docs_dir / "modified.md", "modified document")
    
    # Add existing doc to DB
    doc = Document(
        path_id="modified.md",
        file_path="modified.md",
        checksum="12345678"
    )
    added = await document_service.repository.add(doc)
    
    # Run sync
    await sync_service.sync(root_dir)
    
    # Verify results
    documents = await document_service.repository.find_all()
    assert len(documents) == 2
    
    paths = {d.path_id for d in documents}
    assert "new.md" in paths
    assert "modified.md" in paths
        
    


@pytest.mark.asyncio
async def test_sync_knowledge(
    sync_service: SyncService,
    root_dir: Path,
    entity_service: EntityService
):
    """Test syncing knowledge files."""
    # Create test files
    knowledge_dir = root_dir / "knowledge"
    
    # New entity with relation
    new_content = """
---
type: concept
id: concept/test_concept
created: 2023-01-01
modified: 2023-01-01
---
# Test Concept

A test concept.

## Observations
- [design] Core feature

## Relations
- depends_on [[concept/other]]
"""
    await create_test_file(knowledge_dir / "concept/test_concept.md", new_content)
    
    # Create related entity in DB
    other = Entity(
        path_id="concept/other",
        name="Other",
        entity_type="concept",
        file_path="concept/other.md"
    )
    await entity_service.repository.add(other)
    
    # Run sync
    await sync_service.sync(root_dir)
    
    # Verify results
    entities = await entity_service.repository.find_all()
    assert len(entities) == 2
    
    # Find new entity
    test_concept: Entity = next(e for e in entities if e.path_id == "concept/test_concept")
    assert test_concept.entity_type == "concept"
    
    # Verify relation was created
    entity = await entity_service.get_by_path_id(test_concept.path_id)
    relations = entity.relations
    assert len(relations) == 1
    assert relations[0].relation_type == "depends_on"
    assert relations[0].to_id == other.id


@pytest.mark.asyncio
async def test_sync_deletes(
    sync_service: SyncService,
    root_dir: Path,
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
    await sync_service.sync(root_dir)
    
    # Verify deletions
    docs = await document_service.repository.find_all()
    assert len(docs) == 0
        
    entities = await entity_service.repository.find_all()
    assert len(entities) == 0