"""Tests for knowledge graph API endpoints."""
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from icecream import ic
from loguru import logger

from basic_memory.deps import get_project_config, get_engine


@pytest_asyncio.fixture
def app(test_config, engine) -> FastAPI:
    """Create FastAPI test application."""
    # Lazy import router to avoid app startup issues
    from basic_memory.api.routers.knowledge import router

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_project_config] = lambda: test_config
    app.dependency_overrides[get_engine] = lambda: engine
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create client using ASGI transport - same as CLI will use."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_create_entities(client: AsyncClient):
    """Should create entities successfully."""
    # Create an entity
    response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test"
        }]
    })

    # Verify creation
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 1
    entity = data["entities"][0]
    assert entity["id"] == "test/test_entity"
    assert entity["name"] == "Test Entity"

    entity_type = entity.get("entity_type") or entity.get("entityType")
    assert entity_type == "test"


@pytest.mark.asyncio
async def test_get_entity(client: AsyncClient):
    """Should retrieve an entity by ID."""
    # First create an entity
    create_response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test",
        }]
    })
    entity_id = create_response.json()["entities"][0]["id"]

    # Now get it by ID
    response = await client.get(f"/knowledge/entities/{entity_id}")

    # Verify retrieval
    assert response.status_code == 200
    entity = response.json()
    assert entity["id"] == entity_id
    assert entity["name"] == "Test Entity"

    entity_type = entity.get("entity_type") or entity.get("entityType")
    assert entity_type == "test"



@pytest.mark.asyncio
async def test_create_relations(client: AsyncClient):
    """Should create relations between entities."""
    # Create two entities to relate
    entities = [
        {"name": "Source Entity", "entity_type": "test"},
        {"name": "Target Entity", "entity_type": "test"}
    ]
    create_response = await client.post("/knowledge/entities", json={"entities": entities})
    created = create_response.json()["entities"]
    source_id = created[0]["id"]
    target_id = created[1]["id"]

    # Create relation between them
    response = await client.post("/knowledge/relations", json={
        "relations": [{
            "from_id": source_id,
            "to_id": target_id,
            "relation_type": "related_to"
        }]
    })

    logger.debug("response: %s", response.json())

    # Verify relation
    assert response.status_code == 200
    data = response.json()
    assert len(data["relations"]) == 1
    relation = data["relations"][0]
    assert relation["from_id"] == source_id
    assert relation["to_id"] == target_id
    assert relation["relation_type"] == "related_to"


@pytest.mark.asyncio
async def test_add_observations(client: AsyncClient):
    """Should add observations to an entity."""
    # Create an entity first
    create_response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test"
        }]
    })
    entity_id = create_response.json()["entities"][0]["id"]

    # Add observations
    response = await client.post("/knowledge/observations", json={
        "entity_id": entity_id,
        "observations": [
            "First observation",
            "Second observation"
        ]
    })

    logger.debug(ic(response.content))

    # Verify observations were added
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == entity_id
    assert len(data["observations"]) == 2
    assert data["observations"][0]["content"] == "First observation"
    assert data["observations"][1]["content"] == "Second observation"

    # Verify observations appear in entity
    entity_response = await client.get(f"/knowledge/entities/{entity_id}")
    entity = entity_response.json()
    assert len(entity["observations"]) == 2


@pytest.mark.asyncio
async def test_search_nodes(client: AsyncClient):
    """Should search for entities in the knowledge graph."""
    # Create a few entities with different names
    entities = [
        {"name": "Not found", "entity_type": "negative"},
        {"name": "Alpha Test", "entity_type": "test"},
        {"name": "Beta Test", "entity_type": "test"},
        {"name": "Gamma Production", "entity_type": "test"} #match entity_type
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # Search for "Test" in names
    response = await client.post("/knowledge/search", json={"query": "Test"})

    # Verify search results
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Test"
    assert len(data["matches"]) == 3
    names = [entity["name"] for entity in data["matches"]]
    assert "Alpha Test" in names
    assert "Beta Test" in names
    assert "Gamma Production" in names


@pytest.mark.asyncio
async def test_full_knowledge_flow(client: AsyncClient):
    """Test a complete knowledge graph flow with multiple operations."""
    # 1. Create main entity
    main_response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "Main Entity",
            "entity_type": "test"
        },
        {
            "name": "Non Entity",
            "entity_type": "n_a"
        }]
    })
    main_id = main_response.json()["entities"][0]["id"]
    assert main_response.status_code == 200
    assert main_id is not None

    # 2. Create related entities
    related_response = await client.post("/knowledge/entities", json={
        "entities": [
            {"name": "Related One", "entity_type": "test"},
            {"name": "Related Two", "entity_type": "test"}
        ]
    })
    related = related_response.json()["entities"]
    related_ids = [e["id"] for e in related]
    assert related_response.status_code == 200
    assert len(related_ids) == 2

    # 3. Add relations
    relations_response = await client.post("/knowledge/relations", json={
        "relations": [
            {
                "from_id": main_id,
                "to_id": related_ids[0],
                "relation_type": "connects_to"
            },
            {
                "from_id": main_id,
                "to_id": related_ids[1],
                "relation_type": "connects_to"
            }
        ]
    })
    assert relations_response.status_code == 200
    assert len(relations_response.json()["relations"]) == 2

    # 4. Add observations to main entity
    await client.post("/knowledge/observations", json={
        "entity_id": main_id,
        "observations": [
            "Connected to first related entity",
            "Connected to second related entity"
        ]
    })

    # 5. Verify full graph structure
    main_get = await client.get(f"/knowledge/entities/{main_id}")
    main_entity = main_get.json()

    # Check entity structure
    assert main_entity["name"] == "Main Entity"
    assert len(main_entity["observations"]) == 2
    assert len(main_entity["relations"]) == 2

    # 6. Search should find all related entities
    search = await client.post("/knowledge/search", json={"query": "Related"})
    matches = search.json()["matches"]
    assert len(matches) == 3  # Should find both related entities