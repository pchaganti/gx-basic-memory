"""Tests for knowledge graph API endpoints."""
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from icecream import ic
from loguru import logger

from basic_memory.api.routers.knowledge import router
from basic_memory.api.deps import MemoryServiceDep
from basic_memory.models import Entity, Relation, Observation


@pytest_asyncio.fixture
def app(memory_service_mock: AsyncMock) -> FastAPI:
    """Create FastAPI test application."""
    app = FastAPI()
    app.include_router(router)
    
    async def override_get_memory_service() -> MemoryServiceDep:
        async def get_service():
            yield memory_service_mock
        return get_service()
    
    app.dependency_overrides[MemoryServiceDep] = override_get_memory_service
    return app
    return app

@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    base_url = "http://test"

    async with AsyncClient(transport=transport, base_url=base_url) as client:
        yield client

@pytest_asyncio.fixture
def memory_service_mock() -> AsyncMock:
    """Create mock memory service."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_entities(client: AsyncClient, memory_service_mock: AsyncMock):
    """Should create new entities successfully."""
    # Setup mock response
    entity = Entity(id="test-1", name="Test Entity", entity_type="test")
    memory_service_mock.create_entities.return_value = [entity]
    
    # Make request
    response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test"
        }]
    })

    logger.debug(ic(response.content))
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 1
    assert data["entities"][0]["id"] == "test-1"
    assert data["entities"][0]["name"] == "Test Entity"
    
    # Verify service called
    memory_service_mock.create_entities.assert_called_once()

@pytest.mark.asyncio
async def test_get_entity(client: AsyncClient, memory_service_mock: AsyncMock):
    """Should retrieve a single entity by ID."""
    # Setup mock
    entity = Entity(
        id="test-1", 
        name="Test Entity",
        entity_type="test",
        observations=[
            Observation(id=1, content="Test observation")
        ]
    )
    memory_service_mock.get_entity.return_value = entity
    
    # Make request
    response = await client.get("/knowledge/entities/test-1")
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-1"
    assert data["name"] == "Test Entity"
    assert len(data["observations"]) == 1
    
    # Verify service called
    memory_service_mock.get_entity.assert_called_once_with("test-1")


@pytest.mark.asyncio
async def test_create_relations(client: AsyncClient, memory_service_mock: AsyncMock):
    """Should create relations between entities."""
    # Setup mock
    relation = Relation(
        id=1,
        from_entity_id="test-1",
        to_entity_id="test-2",
        relation_type="related_to"
    )
    memory_service_mock.create_relations.return_value = [relation]
    
    # Make request
    response = await client.post("/knowledge/relations", json={
        "relations": [{
            "from_entity_id": "test-1",
            "to_entity_id": "test-2",
            "relation_type": "related_to"
        }]
    })
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert len(data["relations"]) == 1
    assert data["relations"][0]["from_entity_id"] == "test-1"
    assert data["relations"][0]["to_entity_id"] == "test-2"
    
    # Verify service called
    memory_service_mock.create_relations.assert_called_once()


@pytest.mark.asyncio
async def test_add_observations(client: AsyncClient, memory_service_mock: AsyncMock):
    """Should add observations to an entity."""
    # Setup mock
    observations = [
        Observation(id=1, content="Test observation 1"),
        Observation(id=2, content="Test observation 2")
    ]
    memory_service_mock.add_observations.return_value = observations
    
    # Make request
    response = await client.post("/knowledge/observations", json={
        "entity_id": "test-1",
        "observations": [
            "Test observation 1",
            "Test observation 2"
        ]
    })
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "test-1"
    assert len(data["observations"]) == 2
    assert data["observations"][0]["content"] == "Test observation 1"
    
    # Verify service called
    memory_service_mock.add_observations.assert_called_once()


@pytest.mark.asyncio
async def test_search_nodes(client: AsyncClient, memory_service_mock: AsyncMock):
    """Should search for entities in the knowledge graph."""
    # Setup mock
    entity = Entity(id="test-1", name="Test Entity", entity_type="test")
    memory_service_mock.search_nodes.return_value = [entity]
    
    # Make request
    response = await client.post("/knowledge/search", json={
        "query": "test"
    })
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test"
    assert len(data["matches"]) == 1
    assert data["matches"][0]["id"] == "test-1"
    
    # Verify service called
    memory_service_mock.search_nodes.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_create_entities_validation(client: AsyncClient):
    """Should validate entity creation input."""
    # Make request with invalid data
    response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "",  # Empty name should fail validation
            "entity_type": "test"
        }]
    })
    
    # Assert validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_relations_validation(client: AsyncClient):
    """Should validate relation creation input."""
    # Make request with invalid data
    response = await client.post("/knowledge/relations", json={
        "relations": [{
            "from_entity_id": "",  # Empty ID should fail validation
            "to_entity_id": "test-2",
            "relation_type": "related_to"
        }]
    })
    
    # Assert validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_observations_validation(client: AsyncClient):
    """Should validate observation input."""
    # Make request with invalid data
    response = await client.post("/knowledge/observations", json={
        "entity_id": "",  # Empty ID should fail validation
        "observations": []  # Empty observations should fail validation
    })
    
    # Assert validation error
    assert response.status_code == 422
