"""Tests for observation schema validation and categories."""

import pytest
from pydantic import ValidationError

from basic_memory.schemas import ObservationResponse
from basic_memory.schemas.base import ObservationCategory
from basic_memory.schemas.request import ObservationCreate


def test_observation_create_minimal():
    """Test creating ObservationCreate with minimal fields."""
    data = {"content": "Test observation"}
    obs = ObservationCreate.model_validate(data)
    assert obs.content == "Test observation"
    assert obs.category == ObservationCategory.NOTE  # Default category


def test_observation_create_complete():
    """Test creating ObservationCreate with all fields."""
    data = {"content": "Test observation", "category": "tech", "context": "Test context"}
    obs = ObservationCreate.model_validate(data)
    assert obs.content == "Test observation"
    assert obs.category == ObservationCategory.TECH


def test_observation_create_category_validation():
    """Test category validation in ObservationCreate."""
    # Valid categories
    for category in ObservationCategory:
        data = {"content": "Test", "category": category.value}
        obs = ObservationCreate.model_validate(data)
        assert obs.category == category

    # Invalid category
    with pytest.raises(ValidationError):
        ObservationCreate.model_validate({"content": "Test", "category": "invalid_category"})


def test_observation_response():
    """Test ObservationResponse validation and conversion."""
    data = {
        "id": 1,
        "permalink": 1,
        "content": "Test observation",
        "category": "tech",
        "context": "Test context",
        "created_at": "2024-12-25T12:00:00",
        "updated_at": "2024-12-25T12:00:00",
    }
    obs = ObservationResponse.model_validate(data)
    assert obs.content == "Test observation"
    assert obs.category == ObservationCategory.TECH
    assert obs.context == "Test context"


def test_observation_create_empty_content():
    """Test validation of empty content."""
    with pytest.raises(ValidationError):
        ObservationCreate.model_validate({"content": "", "category": "tech"})

    with pytest.raises(ValidationError):
        ObservationCreate.model_validate(
            {
                "content": " ",  # Just whitespace
                "category": "tech",
            }
        )


def test_observation_create_content_length():
    """Test content length validation."""
    # Create string just over max length
    long_content = "x" * 1001

    with pytest.raises(ValidationError):
        ObservationCreate.model_validate({"content": long_content, "category": "tech"})


def test_observation_category_coercion():
    """Test category accepts both string and enum."""
    # Test with string
    obs1 = ObservationCreate.model_validate({"content": "Test", "category": "tech"})
    assert obs1.category == ObservationCategory.TECH

    # Test with enum
    obs2 = ObservationCreate.model_validate(
        {"content": "Test", "category": ObservationCategory.TECH}
    )
    assert obs2.category == ObservationCategory.TECH

    # Both should be equal
    assert obs1.category == obs2.category


def test_observation_category_case_insensitive():
    """Test category validation is case insensitive."""
    variations = ["TECH", "tech", "Tech", "TEcH"]

    for variant in variations:
        obs = ObservationCreate.model_validate({"content": "Test", "category": variant})
        assert obs.category == ObservationCategory.TECH
