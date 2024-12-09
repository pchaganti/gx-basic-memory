"""Tests for the MemoryService class."""
import pytest
from basic_memory.services import MemoryService
from basic_memory.fileio import read_entity_file
from basic_memory.models import Entity as EntityModel, Observation, Relation
from basic_memory.schemas import EntityIn, CreateEntitiesInput, AddObservationsInput

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

    entity_input = CreateEntitiesInput.model_validate({"entities": test_entities_data})
    entities = await memory_service.create_entities(entity_input.entities)

    # Verify the SQLAlchemy models were created
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

    # Verify files were created (returns Pydantic Entity)
    file_entity1 = await read_entity_file(memory_service.entities_path, entities[0].id)
    file_entity2 = await read_entity_file(memory_service.entities_path, entities[1].id)
    
    assert file_entity1.name == "Test_Entity_1"
    assert file_entity2.name == "Test_Entity_2"

@pytest.mark.asyncio
async def test_add_observations(memory_service: MemoryService):
    """Should add observations to an existing entity."""
    entity_input = CreateEntitiesInput.model_validate({"entities": test_entities_data})
    entities = await memory_service.create_entities([entity_input.entities[0]])
    entity = entities[0]

    # Create observations input
    observations_data = {
        "entity_id": entity.id,
        "observations": [
            {"content": "New observation 1"},
            {"content": "New observation 2", "context": "test context"}
        ]
    }

    # Add observations - returns List[models.Observation]
    observation_input = AddObservationsInput.model_validate(observations_data)
    added_observations = await memory_service.add_observations(observation_input)

    # Check the SQLAlchemy model results
    assert len(added_observations) == 2
    assert added_observations[0].content == "New observation 1"
    assert added_observations[0].context is None
    assert added_observations[1].content == "New observation 2" 
    assert added_observations[1].context == "test context"

    # Verify file was updated - returns Pydantic Entity
    updated_entity = await read_entity_file(memory_service.entities_path, entity.id)
    assert len(updated_entity.observations) == 4  # 2 original + 2 new
    assert updated_entity.observations[2].content == "New observation 1"
    assert updated_entity.observations[3].content == "New observation 2"
    assert updated_entity.observations[3].context == "test context"

    # Verify database - returns SQLAlchemy Entity
    db_entity = await memory_service.entity_service.get_entity(entity.id)
    assert len(db_entity.observations) == 4

@pytest.mark.asyncio
async def test_add_observations_nonexistent_entity(memory_service: MemoryService):
    """Should raise an appropriate error when adding observations to a non-existent entity."""
    observations_data = {
        "entity_id": "nonexistent-id",
        "observations": [{"content": "Test observation"}]
    }
    
    with pytest.raises(Exception) as exc:  # We might want to define a specific error type
        observation_input = AddObservationsInput.model_validate(observations_data)
        await memory_service.add_observations(observation_input)

@pytest.mark.asyncio
async def test_create_relations(memory_service: MemoryService):
    """Should create relations between entities and update both filesystem and database."""
    entity_input = CreateEntitiesInput.model_validate({"entities": test_entities_data})
    entities = await memory_service.create_entities(entity_input.entities)
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

    # Create relations - returns List[models.Relation]
    relations = await memory_service.create_relations(test_relations_data)

    # Verify SQLAlchemy Relation models were created
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

    # Read updated entities from filesystem - returns Pydantic Entities
    updated_entity1 = await read_entity_file(memory_service.entities_path, entity1.id)
    updated_entity2 = await read_entity_file(memory_service.entities_path, entity2.id)

    # Verify relations were added to entity1 in filesystem
    assert len(updated_entity1.relations) == 1
    assert updated_entity1.relations[0].from_id == entity1.id
    assert updated_entity1.relations[0].to_id == entity2.id
    assert updated_entity1.relations[0].relation_type == "connects_to"

    # Verify relations were added to entity2 in filesystem
    assert len(updated_entity2.relations) == 1
    assert updated_entity2.relations[0].from_id == entity2.id
    assert updated_entity2.relations[0].to_id == entity1.id
    assert updated_entity2.relations[0].relation_type == "references"
    assert updated_entity2.relations[0].context == "test context"

    # Now verify database state - get SQLAlchemy Entity models
    db_entity1 = await memory_service.entity_service.get_entity(entity1.id)
    db_entity2 = await memory_service.entity_service.get_entity(entity2.id)

    # Entity 1 should have one outgoing relation to entity 2
    assert len(db_entity1.outgoing_relations) == 1
    outgoing = db_entity1.outgoing_relations[0]
    assert outgoing.from_id == entity1.id
    assert outgoing.to_id == entity2.id
    assert outgoing.relation_type == "connects_to"
    assert outgoing.context is None

    # Entity 1 should have one incoming relation from entity 2
    assert len(db_entity1.incoming_relations) == 1
    incoming = db_entity1.incoming_relations[0]
    assert incoming.from_id == entity2.id
    assert incoming.to_id == entity1.id
    assert incoming.relation_type == "references"
    assert incoming.context == "test context"

    # Verify the same for entity 2 (reversed)
    assert len(db_entity2.outgoing_relations) == 1
    assert len(db_entity2.incoming_relations) == 1

@pytest.mark.asyncio
async def test_create_relations_with_invalid_entity_id(memory_service: MemoryService):
    """Should raise an appropriate error when trying to create relations with non-existent entity IDs."""
    # Create one entity - returns SQLAlchemy Entity
    entity_input = CreateEntitiesInput.model_validate({"entities": test_entities_data})
    entities = await memory_service.create_entities([entity_input.entities[0]])
    entity1 = entities[0]

    # Try to create relation with non-existent entity ID
    bad_relation = {
        "from_id": entity1.id,
        "to_id": "nonexistent-id",
        "relation_type": "connects_to"
    }
    
    with pytest.raises(Exception) as exc:  # We might want to define a specific error type
        await memory_service.create_relations([bad_relation])