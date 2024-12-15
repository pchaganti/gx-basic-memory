"""Tests for Pydantic schema validation and conversion."""
import pytest
from pydantic import ValidationError
from basic_memory.schemas import (
    EntityIn,
    EntityOut,
    RelationIn,
    CreateEntitiesInput,
    SearchNodesInput,
    OpenNodesInput,
)

def test_entity_in_minimal():
    """Test creating EntityIn with minimal required fields."""
    data = {
        "name": "test_entity",
        "entity_type": "test"
    }
    entity = EntityIn.model_validate(data)
    assert entity.name == "test_entity"
    assert entity.entity_type == "test"
    assert entity.description is None
    assert entity.observations == []
    assert entity.relations == []

def test_entity_in_complete():
    """Test creating EntityIn with all fields."""
    data = {
        "name": "test_entity",
        "entity_type": "test",
        "description": "A test entity",
        "observations": [
            "Test observation"
        ],
        "relations": [
            {
                "from_id": "123",
                "to_id": "456",
                "relation_type": "test_relation"
            }
        ]
    }
    entity = EntityIn.model_validate(data)
    assert entity.name == "test_entity"
    assert entity.entity_type == "test"
    assert entity.description == "A test entity"
    assert len(entity.observations) == 1
    assert entity.observations[0] == "Test observation"
    assert len(entity.relations) == 1
    assert entity.relations[0].from_id == "123"

def test_entity_in_validation():
    """Test validation errors for EntityIn."""
    with pytest.raises(ValidationError):
        EntityIn.model_validate({})  # Missing required fields

    with pytest.raises(ValidationError):
        EntityIn.model_validate({"name": "test"})  # Missing entityType

    with pytest.raises(ValidationError):
        EntityIn.model_validate({"entityType": "test"})  # Missing name

def test_relation_in_validation():
    """Test RelationIn validation."""
    data = {
        "from_id": "123",
        "to_id": "456",
        "relation_type": "test"
    }
    relation = RelationIn.model_validate(data)
    assert relation.from_id == "123"
    assert relation.to_id == "456"
    assert relation.relation_type == "test"
    assert relation.context is None

    # With context
    data["context"] = "test context"
    relation = RelationIn.model_validate(data)
    assert relation.context == "test context"

    # Missing required fields
    with pytest.raises(ValidationError):
        RelationIn.model_validate({"from_id": "123", "to_id": "456"})  # Missing relationType

def test_create_entities_input():
    """Test CreateEntitiesInput validation."""
    data = {
        "entities": [
            {
                "name": "entity1",
                "entity_type": "test"
            },
            {
                "name": "entity2",
                "entity_type": "test",
                "description": "test description"
            }
        ]
    }
    create_input = CreateEntitiesInput.model_validate(data)
    assert len(create_input.entities) == 2
    assert create_input.entities[1].description == "test description"

    # Empty entities list should fail
    with pytest.raises(ValidationError):
        CreateEntitiesInput.model_validate({"entities": []})

def test_entity_out_from_attributes():
    """Test EntityOut creation from database model attributes."""
    # Simulate database model attributes
    db_data = {
        "id": "123",
        "name": "test",
        "entity_type": "test",
        "description": "test description",
        "observations": [
            {"id": 1, "content": "test obs", "context": None}
        ],
        "relations": [
            {
                "id": 1,
                "from_id": "123",
                "to_id": "456",
                "relation_type": "test",
                "context": None
            }
        ]
    }
    entity = EntityOut.model_validate(db_data)
    assert entity.id == "123"
    assert entity.description == "test description"
    assert len(entity.observations) == 1
    assert entity.observations[0].id == 1
    assert len(entity.relations) == 1
    assert entity.relations[0].id == 1

def test_optional_fields():
    """Test handling of optional fields."""
    # Create with no optional fields
    entity = EntityIn.model_validate({"name": "test", "entity_type": "test"})
    assert entity.description is None
    assert entity.observations == []
    assert entity.relations == []

    # Create with empty optional fields
    entity = EntityIn.model_validate({
        "name": "test",
        "entity_type": "test",
        "description": None,
        "observations": [],
        "relations": []
    })
    assert entity.description is None
    assert entity.observations == []
    assert entity.relations == []

    # Create with some optional fields
    entity = EntityIn.model_validate({
        "name": "test",
        "entity_type": "test",
        "description": "test",
        "observations": []
    })
    assert entity.description == "test"
    assert entity.observations == []
    assert entity.relations == []

def test_search_nodes_input():
    """Test SearchNodesInput validation."""
    search = SearchNodesInput.model_validate({"query": "test query"})
    assert search.query == "test query"

    with pytest.raises(ValidationError):
        SearchNodesInput.model_validate({})  # Missing required query

def test_open_nodes_input():
    """Test OpenNodesInput validation."""
    open_input = OpenNodesInput.model_validate({"names": ["entity1", "entity2"]})
    assert len(open_input.names) == 2

    # Empty names list should fail
    with pytest.raises(ValidationError):
        OpenNodesInput.model_validate({"names": []})