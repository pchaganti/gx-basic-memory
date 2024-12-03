import pytest
import pytest_asyncio
import tempfile
from pathlib import Path

from basic_memory.service import MemoryService
from basic_memory.db import init_connection

@pytest_asyncio.fixture
async def memory_service():
    """Fixture providing initialized MemoryService with temp directories."""
    # Create temp directory that is cleaned up after the test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Override project path
        test_project_path = Path(temp_dir) / "test-project"
        
        # Initialize database connection
        init_connection("test-project")
        
        # Initialize service with test configuration
        service = MemoryService("test-project")
        service.project_path = test_project_path
        
        # Initialize project structure
        await service.initialize_project()
        
        yield service
        
        # Cleanup happens automatically when temp directory is removed

@pytest.fixture
def sample_entity_files(memory_service):
    """Fixture providing sample markdown files."""
    entity_dir = memory_service.project_path / "entities"
    
    # Create sample files
    files = {
        "test-entity-1": "# Test Entity 1\n\nContent",
        "test-entity-2": "# Test Entity 2\n\nContent"
    }
    
    for name, content in files.items():
        (entity_dir / f"{name}.md").write_text(content)
        
    return files