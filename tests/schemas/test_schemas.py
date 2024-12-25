"""Tests for Pydantic schema validation and conversion."""

import pytest
from pydantic import ValidationError

from basic_memory.schemas import (
    Entity,
    EntityResponse,
    Relation,
    CreateEntityRequest,
    SearchNodesRequest,
    OpenNodesRequest, RelationResponse,
)


def test_entity_in_minimal():
    """Test creating EntityIn with minimal required fields."""
    data = {"name": "test_entity", "entity_type": "test"}
    entity = Entity.model_validate(data)
    assert entity.name == "test_entity"
    assert entity.entity_type == "test"
    assert entity.description is None
    assert entity.observations == []


def test_entity_in_complete():
    """Test creating EntityIn with all fields."""
    data = {
        "name": "test_entity",
        "entity_type": "test",
        "description": "A test entity",
        "observations": ["Test observation"],
    }
    entity = Entity.model_validate(data)
    assert entity.name == "test_entity"
    assert entity.entity_type == "test"
    assert entity.description == "A test entity"
    assert len(entity.observations) == 1
    assert entity.observations[0] == "Test observation"


def test_entity_in_validation():
    """Test validation errors for EntityIn."""
    with pytest.raises(ValidationError):
        Entity.model_validate({})  # Missing required fields

    with pytest.raises(ValidationError):
        Entity.model_validate({"name": "test"})  # Missing entityType

    with pytest.raises(ValidationError):
        Entity.model_validate({"entityType": "test"})  # Missing name


def test_relation_in_validation():
    """Test RelationIn validation."""
    data = {"from_id": "123", "to_id": "456", "relation_type": "test"}
    relation = Relation.model_validate(data)
    assert relation.from_id == "123"
    assert relation.to_id == "456"
    assert relation.relation_type == "test"
    assert relation.context is None

    # With context
    data["context"] = "test context"
    relation = Relation.model_validate(data)
    assert relation.context == "test context"

    # Missing required fields
    with pytest.raises(ValidationError):
        Relation.model_validate({"from_id": "123", "to_id": "456"})  # Missing relationType

def test_relation_response():
    """Test RelationResponse validation."""
    data = {"from_id": 123, "to_id": 456, "relation_type": "test", "from_entity":{"path_id": "123"}, "to_entity":{"path_id": "456"}}
    relation = RelationResponse.model_validate(data)
    assert relation.from_id == "123"
    assert relation.to_id == "456"
    assert relation.relation_type == "test"
    assert relation.context is None


def test_create_entities_input():
    """Test CreateEntitiesInput validation."""
    data = {
        "entities": [
            {"name": "entity1", "entity_type": "test"},
            {"name": "entity2", "entity_type": "test", "description": "test description"},
        ]
    }
    create_input = CreateEntityRequest.model_validate(data)
    assert len(create_input.entities) == 2
    assert create_input.entities[1].description == "test description"

    # Empty entities list should fail
    with pytest.raises(ValidationError):
        CreateEntityRequest.model_validate({"entities": []})


def test_entity_out_from_attributes():
    """Test EntityOut creation from database model attributes."""
    # Simulate database model attributes
    db_data = {
        "id": "123",
        "name": "test",
        "entity_type": "test",
        "description": "test description",
        "observations": [{"id": 1, "content": "test obs", "context": None}],
        "relations": [
            {"id": 1, "from_id": 123, "to_id": 456, "relation_type": "test", "context": None}
        ],
    }
    entity = EntityResponse.model_validate(db_data)
    assert entity.id == 123
    assert entity.description == "test description"
    assert len(entity.observations) == 1
    assert entity.observations[0].id == 1
    assert len(entity.relations) == 1


def test_optional_fields():
    """Test handling of optional fields."""
    # Create with no optional fields
    entity = Entity.model_validate({"name": "test", "entity_type": "test"})
    assert entity.description is None
    assert entity.observations == []

    # Create with empty optional fields
    entity = Entity.model_validate(
        {
            "name": "test",
            "entity_type": "test",
            "description": None,
            "observations": [],
        }
    )
    assert entity.description is None
    assert entity.observations == []

    # Create with some optional fields
    entity = Entity.model_validate(
        {"name": "test", "entity_type": "test", "description": "test", "observations": []}
    )
    assert entity.description == "test"
    assert entity.observations == []


def test_search_nodes_input():
    """Test SearchNodesInput validation."""
    search = SearchNodesRequest.model_validate({"query": "test query"})
    assert search.query == "test query"

    with pytest.raises(ValidationError):
        SearchNodesRequest.model_validate({})  # Missing required query


def test_open_nodes_input():
    """Test OpenNodesInput validation."""
    open_input = OpenNodesRequest.model_validate({"entity_ids": [1, 2]})
    assert len(open_input.entity_ids) == 2

    # Empty names list should fail
    with pytest.raises(ValidationError):
        OpenNodesRequest.model_validate({"entity_ids": []})
