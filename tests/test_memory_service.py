"""Tests for the MemoryService class."""
import pytest

from basic_memory.services import MemoryService

test_entities_data = [
    {
        "name": "Test_Entity_1",
        "entity_type": "test",
        "observations": [{"content":"Observation 1.1"}, {"content":"Observation 1.2"}]
    },
    {
        "name": "Test_Entity_2",
        "entity_type": "test",
        "observations": [{"content":"Observation 2.1"}, {"content":"Observation 2.2"}]
    }
]

@pytest.mark.asyncio
async def test_create_entities(memory_service: MemoryService):
    """Should create multiple entities in parallel with their observations."""
    # Create entities
    entities = await memory_service.create_entities(test_entities_data)

    # Verify the entities were created
    assert len(entities) == 2

    # Check first entity
    assert entities[0].name == "Test_Entity_1"
    assert entities[0].entity_type == "test"
    assert len(entities[0].observations) == 2
    assert entities[0].observations[0].content == "Observation 1.1"
    assert entities[0].observations[1].content == "Observation 1.2"

    # Check second entity
    assert entities[1].name == "Test_Entity_2"
    assert entities[1].entity_type == "test"
    assert len(entities[1].observations) == 2
    assert entities[1].observations[0].content == "Observation 2.1"
    assert entities[1].observations[1].content == "Observation 2.2"

    # Verify files were created
    entity1_path = memory_service.entities_path / entities[0].file_name()
    entity2_path = memory_service.entities_path / entities[1].file_name()
    assert entity1_path.exists()
    assert entity2_path.exists()