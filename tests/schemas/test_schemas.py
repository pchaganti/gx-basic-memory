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
from basic_memory.schemas.base import to_snake_case


def test_entity_in_minimal():
    """Test creating EntityIn with minimal required fields."""
    data = {"name": "test_entity", "entity_type": "knowledge"}
    entity = Entity.model_validate(data)
    assert entity.name == "test_entity"
    assert entity.entity_type == "knowledge"
    assert entity.description is None
    assert entity.observations == []


def test_entity_in_complete():
    """Test creating EntityIn with all fields."""
    data = {
        "name": "test_entity",
        "entity_type": "knowledge",
        "description": "A test entity",
        "observations": ["Test observation"],
    }
    entity = Entity.model_validate(data)
    assert entity.name == "test_entity"
    assert entity.entity_type == "knowledge"
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
    data = {"from_id": "test/123", "to_id": "test/456", "relation_type": "test"}
    relation = Relation.model_validate(data)
    assert relation.from_id == "test/123"
    assert relation.to_id == "test/456"
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
    data = {"from_id": "test/123", "to_id": "test/456", "relation_type": "test", "from_entity":{"path_id": "test/123"}, "to_entity":{"path_id": "test/456"}}
    relation = RelationResponse.model_validate(data)
    assert relation.from_id == "test/123"
    assert relation.to_id == "test/456"
    assert relation.relation_type == "test"
    assert relation.context is None


def test_create_entities_input():
    """Test CreateEntitiesInput validation."""
    data = {
        "entities": [
            {"name": "entity1", "entity_type": "knowledge"},
            {"name": "entity2", "entity_type": "knowledge", "description": "test description"},
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
        "path_id": "test/test",
        "name": "test",
        "entity_type": "knowledge",
        "description": "test description",
        "observations": [{"id": 1, "content": "test obs", "context": None}],
        "relations": [
            {"id": 1, "from_id": "test/test", "to_id": "test/test", "relation_type": "test", "context": None}
        ],
    }
    entity = EntityResponse.model_validate(db_data)
    assert entity.path_id == "test/test"
    assert entity.description == "test description"
    assert len(entity.observations) == 1
    assert len(entity.relations) == 1


def test_optional_fields():
    """Test handling of optional fields."""
    # Create with no optional fields
    entity = Entity.model_validate({"name": "test", "entity_type": "knowledge"})
    assert entity.description is None
    assert entity.observations == []

    # Create with empty optional fields
    entity = Entity.model_validate(
        {
            "name": "test",
            "entity_type": "knowledge",
            "description": None,
            "observations": [],
        }
    )
    assert entity.description is None
    assert entity.observations == []

    # Create with some optional fields
    entity = Entity.model_validate(
        {"name": "test", "entity_type": "knowledge", "description": "test", "observations": []}
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
    open_input = OpenNodesRequest.model_validate({"path_ids": ["test/test", "test/test2"]})
    assert len(open_input.path_ids) == 2

    # Empty names list should fail
    with pytest.raises(ValidationError):
        OpenNodesRequest.model_validate({"path_ids": []})


def test_path_sanitization():
    """Test to_snake_case() handles various inputs correctly."""
    test_cases = [
        ("BasicMemory", "basic_memory"),  # CamelCase
        ("Memory Service", "memory_service"),  # Spaces
        ("memory-service", "memory_service"),  # Hyphens
        ("Memory_Service", "memory_service"),  # Already has underscore
        ("API2Service", "api2_service"),  # Numbers
        ("  Spaces  ", "spaces"),  # Extra spaces
        ("mixedCase", "mixed_case"),  # Mixed case
        ("snake_case_already", "snake_case_already"),  # Already snake case
        ("ALLCAPS", "allcaps"),  # All caps
        ("with.dots", "with_dots"),  # Dots
    ]

    for input_str, expected in test_cases:
        result = to_snake_case(input_str)
        assert result == expected, f"Failed for input: {input_str}"


def test_path_id_generation():
    """Test path_id property generates correct paths."""
    test_cases = [
        (
            {"name": "BasicMemory", "entity_type": "knowledge"},
            "basic_memory"
        ),
        (
            {"name": "Memory Service", "entity_type": "knowledge"},
            "memory_service"
        ),
        (
            {"name": "API Gateway", "entity_type": "knowledge"},
            "api_gateway"
        ),
        (
            {"name": "TestCase1", "entity_type": "knowledge"},
            "test_case1"
        ),
    ]

    for input_data, expected_path in test_cases:
        entity = Entity.model_validate(input_data)
        assert entity.path_id == expected_path, f"Failed for input: {input_data}"

