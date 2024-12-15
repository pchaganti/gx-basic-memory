"""Tests for MemoryService delete operations."""

import pytest
from basic_memory.services import MemoryService
from basic_memory.fileio import read_entity_file
from basic_memory.schemas import CreateEntityRequest, CreateRelationsRequest, AddObservationsRequest, Relation

test_create_entity_input = [
    {
        "name": "Test_Entity_1",
        "entity_type": "test",
        "observations": ["Observation 1.1", "Observation 1.2"]
    },
    {
        "name": "Test_Entity_2",
        "entity_type": "test",
        "observations": ["Observation 2.1", "Observation 2.2"]
    }
]


@pytest.mark.asyncio
async def test_create_entities(memory_service: MemoryService):
    """Should create multiple entities in parallel with their observations."""

    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
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

    # Verify files are present
    for entity in entities:
        entity_file_path = memory_service.get_entity_file_path(entity.id)
        assert entity_file_path.exists()


@pytest.mark.asyncio
async def test_add_observations(memory_service: MemoryService):
    """Should add observations to an existing entity."""
    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
    entities = await memory_service.create_entities([entity_input.entities[0]])
    entity = entities[0]

    # Create observations input
    observations_data = {
        "entity_id": entity.id,
        "observations": [
            "New observation 1",
            "New observation 2"
        ]
    }

    # Add observations - returns List[models.Observation]
    observation_input = AddObservationsRequest.model_validate(observations_data)
    added_observations = await memory_service.add_observations(observation_input)

    # Check the SQLAlchemy model results
    assert len(added_observations) == 2
    assert added_observations[0].content == "New observation 1"
    assert added_observations[0].context is None
    assert added_observations[1].content == "New observation 2"
    assert added_observations[1].context is None

    # Verify file was updated - returns Pydantic Entity
    updated_entity = await read_entity_file(memory_service.entities_path, entity.id)
    assert len(updated_entity.observations) == 4  # 2 original + 2 new
    # assert updated_entity.observations[2] == "New observation 1"
    # assert updated_entity.observations[3] == "New observation 2"

    # Verify database - returns SQLAlchemy Entity
    db_entity = await memory_service.entity_service.get_entity(entity.id)
    assert len(db_entity.observations) == 4


@pytest.mark.asyncio
async def test_add_observations_nonexistent_entity(memory_service: MemoryService):
    """Should raise an appropriate error when adding observations to a non-existent entity."""
    observations_data = {
        "entity_id": "nonexistent-id",
        "observations": ["Test observation"]
    }

    with pytest.raises(Exception) as exc:  # We might want to define a specific error type
        observation_input = AddObservationsRequest.model_validate(observations_data)
        await memory_service.add_observations(observation_input)


@pytest.mark.asyncio
async def test_create_relations(memory_service: MemoryService):
    """Should create relations between entities and update both filesystem and database."""
    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
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
    input_args = CreateRelationsRequest.model_validate({"relations": test_relations_data})
    relations = await memory_service.create_relations(input_args.relations)

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
    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
    entities = await memory_service.create_entities([entity_input.entities[0]])
    entity1 = entities[0]

    # Try to create relation with non-existent entity ID
    bad_relation = {
        "from_id": entity1.id,
        "to_id": "nonexistent-id",
        "relation_type": "connects_to"
    }

    with pytest.raises(Exception) as exc:  # We might want to define a specific error type
        await memory_service.create_relations([Relation.model_validate(bad_relation)])


@pytest.mark.asyncio
async def test_delete_entities(memory_service: MemoryService):
    """Test deleting an entity deletes file and database record."""
    # Write the entity files
    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
    entities = await memory_service.create_entities(entity_input.entities)

    # Verify files are present
    for entity in entities:
        entity_file_path = memory_service.get_entity_file_path(entity.id)
        assert entity_file_path.exists()

    # Delete the entities
    result = await memory_service.delete_entities([entity.id for entity in entities])
    assert result is True
    
    # Verify files are gone
    for entity in entities:
        assert not memory_service.get_entity_file_path(entity.id).exists()
    
    # Verify database records are deleted
    for entity in entities:
        deleted = await memory_service.entity_service.entity_repo.find_by_id(entity.id)
        assert deleted is None

@pytest.mark.asyncio
async def test_delete_entity_cascades(memory_service):
    """Test deleting an entity cascades to observations."""

    # Write the entity files
    create_entity_input = test_create_entity_input[0]
    entity_input = CreateEntityRequest.model_validate({"entities": [create_entity_input]})
    entities = await memory_service.create_entities(entity_input.entities)
    assert len(entities) == 1
    test_entity = entities[0]

    # Delete the entity
    result = await memory_service.delete_entities([test_entity.id])
    assert result is True
    
    # Verify file is gone
    assert not memory_service.get_entity_file_path(test_entity.id).exists()
    
    # Verify observations are gone from database
    obsv = await memory_service.observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(obsv) == 0

    # Verify observations are gone from database
    rels = await memory_service.relation_service.relation_repo.find_by_entity(test_entity.id)
    assert len(rels) == 0

@pytest.mark.asyncio
async def test_delete_observations(memory_service):
    """Test deleting specific observations."""

    # Set up entity file with observations
    create_entity_input = test_create_entity_input[0]
    create_entity_input['observations'] = ["First observation", "Second observation", "Third observation"]
    create_entity = CreateEntityRequest.model_validate({"entities": [create_entity_input]})

    entities = await memory_service.create_entities(create_entity.entities)
    assert len(entities) == 1
    test_entity = entities[0]

    # Delete two observations
    to_delete = ["First observation", "Second observation"]
    result = await memory_service.delete_observations(test_entity.id, to_delete)
    assert result is True
    
    # Verify file updated
    updated_entities = await memory_service.open_nodes([test_entity.id])
    assert len(updated_entities) == 1
    updated_entity = updated_entities[0]
    
    assert len(updated_entity.observations) == 1
    assert updated_entity.observations[0] == "Third observation"
    
    # Verify database updated
    remaining_db = await memory_service.observation_service.observation_repo.find_by_entity(test_entity.id)
    assert len(remaining_db) == 1
    assert remaining_db[0].content == "Third observation"

@pytest.mark.asyncio
async def test_delete_relations(memory_service):
    """Test deleting relations between entities."""
    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
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
    input_args = CreateRelationsRequest.model_validate({"relations": test_relations_data})
    relations = await memory_service.create_relations(input_args.relations)
    
    # Delete the relation
    to_delete = [{
        "from_id": entity1.id,
        "to_id": entity2.id,
        "relation_type": "connects_to"
    }]
    result = await memory_service.delete_relations(to_delete)
    assert result is True
    
    # Verify relation removed from source entity file
    # Verify file updated
    updated_entities = await memory_service.open_nodes([entity1.id])
    assert len(updated_entities) == 1
    updated_entity = updated_entities[0]

    assert len(updated_entity.relations) == 0
    
    # Verify relation removed from database
    relations = await memory_service.relation_service.relation_repo.find_by_entities(entity1.id, entity2.id)
    assert len(relations) == 0

@pytest.mark.asyncio
async def test_delete_nonexistent_entity(memory_service):
    """Test deleting an entity that doesn't exist."""
    result = await memory_service.delete_entities(["nonexistent/id"])
    assert result is False

@pytest.mark.asyncio
async def test_delete_nonexistent_observations(memory_service):
    """Test deleting observations that don't exist."""

    # Set up entity file with observations
    create_entity_input = test_create_entity_input[0]
    create_entity_input['observations'] = ["First observation", "Second observation", "Third observation"]
    create_entity = CreateEntityRequest.model_validate({"entities": [create_entity_input]})

    entities = await memory_service.create_entities(create_entity.entities)
    assert len(entities) == 1
    test_entity = entities[0]
    
    result = await memory_service.delete_observations(test_entity.id, ["Nonexistent"])
    assert result is False

@pytest.mark.asyncio
async def test_delete_nonexistent_relations(memory_service):
    """Test deleting relations that don't exist."""
    entity_input = CreateEntityRequest.model_validate({"entities": test_create_entity_input})
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
    input_args = CreateRelationsRequest.model_validate({"relations": test_relations_data})
    relations = await memory_service.create_relations(input_args.relations)
    
    to_delete = [{
        "from_id": entity1.id,
        "to_id": entity2.id,
        "relation_type": "nonexistent"
    }]
    result = await memory_service.delete_relations(to_delete)
    assert result is False