"""Tests for knowledge graph API routes."""

from typing import List
from urllib.parse import quote

import pytest
from httpx import AsyncClient

from basic_memory.schemas import (
    EntityResponse,
    CreateEntityResponse,
    ObservationResponse,
    RelationResponse,
)


async def create_entity(client) -> EntityResponse:
    data = {
        "name": "TestEntity",
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

    assert entity["name"] == data["name"]
    entity_type = entity.get("entity_type")
    assert entity_type == data["entity_type"]

    assert len(entity["observations"]) == 2

    create_response = CreateEntityResponse.model_validate(response_data)
    return create_response.entities[0]


async def add_observations(client, path_id: str) -> List[ObservationResponse]:
    response = await client.post(
        "/knowledge/observations",
        json={"entity_id": path_id, "observations": ["First observation", "Second observation"]},
    )
    # Verify observations were added
    assert response.status_code == 200
    data = response.json()

    obs_response = EntityResponse.model_validate(data)
    return obs_response.observations


async def create_related_entities(client) -> List[RelationResponse]:  # pyright: ignore [reportReturnType]
    # Create two entities to relate
    entities = [
        {"name": "SourceEntity", "entity_type": "test"},
        {"name": "TargetEntity", "entity_type": "test"},
    ]
    create_response = await client.post("/knowledge/entities", json={"entities": entities})
    created = create_response.json()["entities"]
    source_path_id = "test/source_entity"
    target_path_id = "test/target_entity"

    # Create relation between them
    response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {"from_id": source_path_id, "to_id": target_path_id, "relation_type": "related_to"}
            ]
        },
    )

    # Verify relation
    assert response.status_code == 200
    data = response.json()

    relation_response = CreateEntityResponse.model_validate(data)
    assert len(relation_response.entities) == 2

    source_entity = relation_response.entities[0]
    target_entity = relation_response.entities[1]

    assert len(source_entity.relations) == 1
    source_relation = source_entity.relations[0]
    assert source_relation.from_id == source_path_id
    assert source_relation.to_id == target_path_id

    assert len(target_entity.relations) == 1
    target_relation = target_entity.relations[0]
    assert target_relation.from_id == source_path_id
    assert target_relation.to_id == target_path_id

    return source_entity.relations + target_entity.relations


@pytest.mark.asyncio
async def test_create_entities(client: AsyncClient):
    """Should create entities successfully."""
    await create_entity(client)


@pytest.mark.asyncio
async def test_get_entity(client: AsyncClient):
    """Should retrieve an entity by path ID."""
    # First create an entity
    data = {"name": "TestEntity", "entity_type": "test"}
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    assert response.status_code == 200
    data = response.json()

    # Now get it by path
    path_id = data["entities"][0]["path_id"]
    response = await client.get(f"/knowledge/entities/{path_id}")

    # Verify retrieval
    assert response.status_code == 200
    entity = response.json()
    assert entity["name"] == "TestEntity"
    assert entity["entity_type"] == "test"
    assert entity["path_id"] == "test/test_entity"


@pytest.mark.asyncio
async def test_create_relations(client: AsyncClient):
    """Should create relations between entities."""
    await create_related_entities(client)


@pytest.mark.asyncio
async def test_add_observations(client: AsyncClient):
    """Should add observations to an entity."""
    # Create an entity first
    data = {"name": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [data]})

    path_id = "test/test_entity"
    # Add observations
    await add_observations(client, path_id)

    # Verify observations appear in entity
    entity_response = await client.get(f"/knowledge/entities/{path_id}")
    entity = entity_response.json()
    assert len(entity["observations"]) == 2


@pytest.mark.asyncio
async def test_search_nodes(client: AsyncClient):
    """Should search for entities in the knowledge graph."""
    # Create a few entities with different names
    entities = [
        {"name": "NotFound", "entity_type": "negative"},
        {"name": "AlphaTest", "entity_type": "test"},
        {"name": "BetaTest", "entity_type": "test"},
        {"name": "GammaProduction", "entity_type": "test"},  # match entity_type
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # Search for "Test" in names
    response = await client.post("/knowledge/search", json={"query": "Test"})

    # Verify search results
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Test"
    assert len(data["matches"]) == 3
    names = {entity["name"] for entity in data["matches"]}
    assert names == {"AlphaTest", "BetaTest", "GammaProduction"}


@pytest.mark.asyncio
async def test_open_nodes(client: AsyncClient):
    """Should open multiple nodes by path IDs."""
    # Create a few entities with different names
    entities = [
        {"name": "AlphaTest", "entity_type": "test"},
        {"name": "BetaTest", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # Open nodes by path IDs
    response = await client.post(
        "/knowledge/nodes",
        json={"entity_ids": ["test/alpha_test"]},
    )

    # Verify results
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 1
    entity = data["entities"][0]
    assert entity["name"] == "AlphaTest"
    assert entity["entity_type"] == "test"
    assert entity["path_id"] == "test/alpha_test"


@pytest.mark.asyncio
async def test_delete_entity(client: AsyncClient):
    """Test DELETE /knowledge/entities with path ID."""
    # Create test entity
    entity_data = {"name": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})

    # Test deletion
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": ["test/TestEntity"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify entity is gone
    path_id = quote("test/TestEntity")
    response = await client.get(f"/knowledge/entities/{path_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_bulk(client: AsyncClient):
    """Test bulk entity deletion using path IDs."""
    # Create test entities
    entities = [
        {"name": "Entity1", "entity_type": "test"},
        {"name": "Entity2", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # Test deletion
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": ["test/Entity1", "test/Entity2"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify entities are gone
    for name in ["Entity1", "Entity2"]:
        path_id = quote(f"test/{name}")
        response = await client.get(f"/knowledge/entities/{path_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_with_observations(client, observation_repository):
    """Test cascading delete with observations."""
    # Create test entity and add observations
    entity_data = {"name": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})
    await add_observations(client, "test/TestEntity")

    # Delete entity
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": ["test/TestEntity"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify observations are gone
    observations = await observation_repository.find_all()
    assert len(observations) == 0


@pytest.mark.asyncio
async def test_delete_observations(client, observation_repository):
    """Test deleting specific observations."""
    # Create entity and add observations
    entity_data = {"name": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})
    observations = await add_observations(client, "test/TestEntity")  # adds 2

    # Delete specific observations
    request_data = {"entity_id": "test/TestEntity", "deletions": [observations[0].content]}
    response = await client.post("/knowledge/observations/delete", json=request_data)
    assert response.status_code == 200
    data = response.json()

    del_response = EntityResponse.model_validate(data)
    assert len(del_response.observations) == 1
    assert del_response.observations[0].content == observations[1].content


@pytest.mark.asyncio
async def test_delete_relations(client, relation_repository):
    """Test deleting relations between entities."""
    relations = await create_related_entities(client)
    assert len(relations) == 2
    relation = relations[0]

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
    data = response.json()

    del_response = CreateEntityResponse.model_validate(data)
    assert len(del_response.entities) == 2
    assert all(len(e.relations) == 0 for e in del_response.entities)


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(client: AsyncClient):
    """Test deleting a nonexistent entity by path ID."""
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": ["test/non_existent"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}


@pytest.mark.asyncio
async def test_delete_nonexistent_observations(client: AsyncClient):
    """Test deleting nonexistent observations."""
    # Create test entity
    entity_data = {"name": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})

    request_data = {"entity_id": "test/TestEntity", "deletions": ["Nonexistent observation"]}
    response = await client.post("/knowledge/observations/delete", json=request_data)
    assert response.status_code == 200

    data = response.json()
    entity = EntityResponse.model_validate(data)
    assert len(entity.observations) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_relations(client: AsyncClient):
    """Test deleting nonexistent relations."""
    request_data = {
        "relations": [
            {
                "from_id": "test/non_existent1",
                "to_id": "test/non_existent2",
                "relation_type": "nonexistent",
            }
        ]
    }
    response = await client.post("/knowledge/relations/delete", json=request_data)
    assert response.status_code == 200

    data = response.json()
    del_response = CreateEntityResponse.model_validate(data)
    assert del_response.entities == []


@pytest.mark.asyncio
async def test_invalid_path_id_format(client: AsyncClient):
    """Test handling of invalid path ID formats."""
    invalid_path_ids = [
        "no_type_separator",
        "/missing_type/name",
        "type//extra_separator",
        "/",
        "",
    ]
    for invalid_id in invalid_path_ids:
        path_id = quote(invalid_id)
        response = await client.get(f"/knowledge/entities/{path_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_full_knowledge_flow(client: AsyncClient):
    """Test complete knowledge graph flow with path IDs."""
    # 1. Create main entities
    main_entities = [
        {"name": "MainEntity", "entity_type": "test"},
        {"name": "NonEntity", "entity_type": "n_a"},
    ]
    await client.post("/knowledge/entities", json={"entities": main_entities})

    # 2. Create related entities
    related_entities = [
        {"name": "RelatedOne", "entity_type": "test"},
        {"name": "RelatedTwo", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": related_entities})

    # 3. Add relations
    relations_response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {
                    "from_id": "test/main_entity",
                    "to_id": "test/related_one",
                    "relation_type": "connects_to",
                },
                {
                    "from_id": "test/main_entity",
                    "to_id": "test/related_two",
                    "relation_type": "connects_to",
                },
            ]
        },
    )
    assert relations_response.status_code == 200

    # 4. Add observations to main entity
    await client.post(
        "/knowledge/observations",
        json={
            "entity_id": "test/main_entity",
            "observations": [
                "Connected to first related entity",
                "Connected to second related entity",
            ],
        },
    )

    # 5. Verify full graph structure
    path_id = quote("test/MainEntity")
    main_get = await client.get(f"/knowledge/entities/{path_id}")
    main_entity = main_get.json()

    # Check entity structure
    assert main_entity["name"] == "MainEntity"
    assert len(main_entity["observations"]) == 2
    assert len(main_entity["relations"]) == 2

    # 6. Search should find all related entities
    search = await client.post("/knowledge/search", json={"query": "Related"})
    matches = search.json()["matches"]
    assert len(matches) == 3  # Should find both related entities, and the main one with the observation

    # 7. Delete main entity
    response = await client.post(
        "/knowledge/entities/delete", json={"entity_ids": ["test/MainEntity", "test/NonEntity"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify deletion
    path_id = quote("test/MainEntity")
    response = await client.get(f"/knowledge/entities/{path_id}")
    assert response.status_code == 404
