"""Tests for knowledge graph API routes."""

from typing import AsyncGenerator, List

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from basic_memory.deps import get_project_config, get_engine_factory
from basic_memory.models import Entity
from basic_memory.schemas import (
    EntityResponse,
    CreateEntityResponse,
    AddObservationsResponse,
    ObservationResponse,
    CreateRelationsResponse,
    Relation,
)


@pytest_asyncio.fixture
def app(test_config, engine_factory) -> FastAPI:
    """Create FastAPI test application."""
    # Lazy import router to avoid app startup issues
    from basic_memory.api.routers.knowledge import router

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_project_config] = lambda: test_config
    app.dependency_overrides[get_engine_factory] = lambda: engine_factory
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create client using ASGI transport - same as CLI will use."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def create_entity(client) -> EntityResponse:
    data = {
        "name": "Test Entity",
        "entity_type": "test",
        "observations": ["First observation", "Second observation"],
    }
    # Create an entity
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    # Verify creation
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["entities"]) == 1
    entity = response_data["entities"][0]

    assert entity["id"] == Entity.generate_id(entity["entity_type"], entity["name"])
    assert entity["name"] == data["name"]
    entity_type = entity.get("entity_type")
    assert entity_type == data["entity_type"]

    assert len(entity["observations"]) == 2

    create_response = CreateEntityResponse.model_validate(response_data)
    return create_response.entities[0]


async def add_observations(client, entity_id) -> List[ObservationResponse]:
    response = await client.post(
        "/knowledge/observations",
        json={"entity_id": entity_id, "observations": ["First observation", "Second observation"]},
    )
    # Verify observations were added
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == entity_id
    assert len(data["observations"]) == 2
    assert data["observations"][0]["content"] == "First observation"
    assert data["observations"][1]["content"] == "Second observation"

    added = AddObservationsResponse.model_validate(data)
    return added.observations


async def create_related_entities(client) -> List[Relation]:  # pyright: ignore [reportReturnType]
    # Create two entities to relate
    entities = [
        {"name": "Source Entity", "entity_type": "test"},
        {"name": "Target Entity", "entity_type": "test"},
    ]
    create_response = await client.post("/knowledge/entities", json={"entities": entities})
    created = create_response.json()["entities"]
    source_id = created[0]["id"]
    target_id = created[1]["id"]
    # Create relation between them
    response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [{"from_id": source_id, "to_id": target_id, "relation_type": "related_to"}]
        },
    )
    # Verify relation
    assert response.status_code == 200
    data = response.json()
    assert len(data["relations"]) == 1
    relation = data["relations"][0]
    assert relation["from_id"] == source_id
    assert relation["to_id"] == target_id
    assert relation["relation_type"] == "related_to"

    create_response = CreateRelationsResponse.model_validate(data)
    return create_response.relations


@pytest.mark.asyncio
async def test_create_entities(client: AsyncClient):
    """Should create entities successfully."""
    await create_entity(client)


@pytest.mark.asyncio
async def test_get_entity(client: AsyncClient):
    """Should retrieve an entity by ID."""
    # First create an entity
    create_response = await client.post(
        "/knowledge/entities",
        json={
            "entities": [
                {
                    "name": "Test Entity",
                    "entity_type": "test",
                }
            ]
        },
    )
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
    await create_related_entities(client)


@pytest.mark.asyncio
async def test_add_observations(client: AsyncClient):
    """Should add observations to an entity."""
    # Create an entity first
    create_response = await client.post(
        "/knowledge/entities", json={"entities": [{"name": "Test Entity", "entity_type": "test"}]}
    )
    entity_id = create_response.json()["entities"][0]["id"]

    # Add observations
    await add_observations(client, entity_id)

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
        {"name": "Gamma Production", "entity_type": "test"},  # match entity_type
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
async def test_open_nodes(client: AsyncClient):
    """Should search for entities in the knowledge graph."""
    # Create a few entities with different names
    entities = [
        {"name": "Alpha Test", "entity_type": "test"},
        {"name": "Beta Test", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # open nodes
    response = await client.post(
        "/knowledge/nodes",
        json={
            "entity_ids": [
                "test/alpha_test",
            ]
        },
    )

    # Verify search results
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 1
    entity = data["entities"][0]
    assert entity["name"] == "Alpha Test"
    assert entity["entity_type"] == "test"


@pytest.mark.asyncio
async def test_delete_entity(client: AsyncClient):
    """Test DELETE /knowledge/entities/{entity_id}."""
    # Create test entity
    entity = await create_entity(client)

    # Test deletion
    response = await client.post("/knowledge/entities/delete", json={"entity_ids": [entity.id]})
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify entity is gone
    response = await client.get(f"/knowledge/entities/{entity.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_bulk(client: AsyncClient):
    """Test DELETE /knowledge/entities/{entity_id}."""
    # Create test entity
    entity1 = await create_entity(client)

    e2_response = await client.post(
        "/knowledge/entities", json={"entities": [{"name": "Test Entity2", "entity_type": "test"}]}
    )
    create_response = CreateEntityResponse.model_validate(e2_response.json())
    entity2 = create_response.entities[0]

    # Test deletion
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": [entity1.id, entity2.id]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify entities are gone
    response = await client.get(f"/knowledge/entities/{entity1.id}")
    assert response.status_code == 404

    response = await client.get(f"/knowledge/entities/{entity2.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_with_observations(client, observation_repository):
    """Test cascading delete with observations."""
    # Create test data
    entity = await create_entity(client)
    observations = await add_observations(client, entity.id)

    # Delete entity
    response = await client.post("/knowledge/entities/delete", json={"entity_ids": [entity.id]})
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify observations are gone
    remaining = await observation_repository.find_by_entity(entity.id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_observations(client, observation_repository):
    """Test DELETE /knowledge/entities/{entity_id}/observations."""
    # Create test data
    entity = await create_entity(client)
    observations = await add_observations(client, entity.id)  # adds 2

    # Delete specific observations
    request_data = {"entity_id": entity.id, "deletions": [observations[0].content]}
    response = await client.post("/knowledge/observations/delete", json=request_data)
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify only specified observations were deleted
    remaining = await observation_repository.find_by_entity(entity.id)
    assert len(remaining) == 2  # because entity originally had 1
    assert remaining[0].content == observations[1].content


@pytest.mark.asyncio
async def test_delete_relations(client, relation_repository):
    """Test DELETE /knowledge/relations."""
    # Create test data
    relatations = await create_related_entities(client)
    assert len(relatations) == 1
    relation = relatations[0]

    # Delete relation
    request_data = {
        "relations": [
            {
                "from_id": relation.from_id,
                "to_id": relation.to_id,
                "relation_type": relation.relation_type,
            }
        ]
    }
    response = await client.post("/knowledge/relations/delete", json=request_data)
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify relation is gone
    remaining = await relation_repository.find_by_entities(relation.from_id, relation.to_id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(client):
    """Test deleting an entity that doesn't exist."""
    response = await client.post("/knowledge/entities/delete", json={"entity_ids": ["bad_id"]})

    assert response.status_code == 200
    assert response.json() == {"deleted": False}


@pytest.mark.asyncio
async def test_delete_nonexistent_observations(client):
    """Test deleting observations that don't exist."""
    # Create test entity
    entity = await create_entity(client)

    request_data = {"entity_id": entity.id, "deletions": ["Nonexistent observation"]}
    response = await client.post("/knowledge/observations/delete", json=request_data)
    assert response.status_code == 200
    assert response.json() == {"deleted": False}


@pytest.mark.asyncio
async def test_delete_nonexistent_relations(client):
    """Test deleting relations that don't exist."""
    request_data = {
        "relations": [
            {
                "from_id": "source/nonexistent",
                "to_id": "target/nonexistent",
                "relation_type": "nonexistent",
            }
        ]
    }
    response = await client.post("/knowledge/relations/delete", json=request_data)
    assert response.status_code == 200
    assert response.json() == {"deleted": False}


@pytest.mark.asyncio
async def test_full_knowledge_flow(client: AsyncClient):
    """Test a complete knowledge graph flow with multiple operations."""
    # 1. Create main entity
    main_response = await client.post(
        "/knowledge/entities",
        json={
            "entities": [
                {"name": "Main Entity", "entity_type": "test"},
                {"name": "Non Entity", "entity_type": "n_a"},
            ]
        },
    )
    assert main_response.status_code == 200
    main_entity_id = "test/main_entity"
    non_entity_id = "n_a/non_entity"
    assert main_entity_id is not None

    # 2. Create related entities
    related_response = await client.post(
        "/knowledge/entities",
        json={
            "entities": [
                {"name": "Related One", "entity_type": "test"},
                {"name": "Related Two", "entity_type": "test"},
            ]
        },
    )
    related = related_response.json()["entities"]
    related_ids = [e["id"] for e in related]
    assert related_response.status_code == 200
    assert len(related_ids) == 2

    # 3. Add relations
    relations_response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {
                    "from_id": main_entity_id,
                    "to_id": related_ids[0],
                    "relation_type": "connects_to",
                },
                {
                    "from_id": main_entity_id,
                    "to_id": related_ids[1],
                    "relation_type": "connects_to",
                },
            ]
        },
    )
    assert relations_response.status_code == 200
    assert len(relations_response.json()["relations"]) == 2

    # 4. Add observations to main entity
    await client.post(
        "/knowledge/observations",
        json={
            "entity_id": main_entity_id,
            "observations": [
                "Connected to first related entity",
                "Connected to second related entity",
            ],
        },
    )

    # 5. Verify full graph structure
    main_get = await client.get(f"/knowledge/entities/{main_entity_id}")
    main_entity = main_get.json()

    # Check entity structure
    assert main_entity["name"] == "Main Entity"
    assert len(main_entity["observations"]) == 2
    assert len(main_entity["relations"]) == 2

    # 6. Search should find all related entities
    search = await client.post("/knowledge/search", json={"query": "Related"})
    matches = search.json()["matches"]
    assert len(matches) == 3  # Should find both related entities

    # 7. delete entities
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": [main_entity_id, non_entity_id]}
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
