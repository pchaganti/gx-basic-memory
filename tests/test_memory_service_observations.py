"""Tests for observation creation through memory service."""
import pytest
from basic_memory.services.memory_service import MemoryService
from basic_memory.schemas import EntityIn, ObservationIn

pytestmark = pytest.mark.anyio


async def test_create_entity_with_observations(tmp_path, memory_service: MemoryService):
    """Test creating an entity with observations in exactly the same way as create_entities tool."""
    # Mirror exact structure from create_entities tool
    entity_data = {
        "name": "Directory Organization",
        "entityType": "memory",
        "description": "Implemented filesystem organization by entity type",
        "observations": [
            {"content": "Files are now organized by type using directories like entities/project/basic_memory"},
            {"content": "Entity IDs match filesystem paths for better mental model"},
            {"content": "Fixed path handling bugs by adding consistent get_entity_path helper"}
        ]
    }

    # Create entity via memory service
    entity = await memory_service.create_entities([EntityIn(**entity_data)])

    assert len(entity) == 1
    assert entity[0].name == "Directory Organization"
    assert len(entity[0].observations) == 3
