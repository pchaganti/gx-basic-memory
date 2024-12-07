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

@pytest.mark.asyncio
async def test_create_relations(memory_service: MemoryService):
    """Should create relations between entities and update the filesystem."""
    # First create the entities
    entities = await memory_service.create_entities(test_entities_data)
    entity1, entity2 = entities

    # Create test relations data using actual entity IDs
    test_relations_data = [
        {
            "from_id": entity1.id,
            "to_id": entity2.id,
            "relation_type": "connects_to"
        },
        {
            "from_id": entity2.id,
            "to_id": entity1.id,
            "relation_type": "references",
            "context": "test context"
        }
    ]

    # Create relations
    relations = await memory_service.create_relations(test_relations_data)

    # Verify relations were created
    assert len(relations) == 2

    # Check first relation
    assert relations[0].from_id == entity1.id
    assert relations[0].to_id == entity2.id
    assert relations[0].relation_type == "connects_to"
    assert relations[0].context is None

    # Check second relation
    assert relations[1].from_id == entity2.id
    assert relations[1].to_id == entity1.id
    assert relations[1].relation_type == "references"
    assert relations[1].context == "test context"

    # Verify relations were added to the entities
    # Read updated entity1 from filesystem
    entity1_path = memory_service.entities_path / entity1.file_name()
    assert entity1_path.exists()
    assert len(entity1.relations) == 1
    assert entity1.relations[0].from_id == entity1.id
    assert entity1.relations[0].to_id == entity2.id
    assert entity1.relations[0].relation_type == "connects_to"

    # Read updated entity2 from filesystem
    entity2_path = memory_service.entities_path / entity2.file_name()
    assert entity2_path.exists()
    assert len(entity2.relations) == 1
    assert entity2.relations[0].from_id == entity2.id
    assert entity2.relations[0].to_id == entity1.id
    assert entity2.relations[0].relation_type == "references"
    assert entity2.relations[0].context == "test context"

@pytest.mark.asyncio
async def test_create_relations_with_invalid_entity_id(memory_service: MemoryService):
    """Should raise an appropriate error when trying to create relations with non-existent entity IDs."""
    # Create only one entity
    entities = await memory_service.create_entities([test_entities_data[0]])
    entity1 = entities[0]

    # Try to create relation with non-existent entity ID
    bad_relation = {
        "from_id": entity1.id,
        "to_id": "nonexistent-id",
        "relation_type": "connects_to"
    }
    
    with pytest.raises(Exception) as exc:  # We might want to define a specific error type
        await memory_service.create_relations([bad_relation])
