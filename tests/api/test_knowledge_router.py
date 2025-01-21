"""Tests for knowledge graph API routes."""

from typing import List
from urllib.parse import quote

import pytest
from httpx import AsyncClient

from basic_memory.schemas import (
    EntityResponse,
    EntityListResponse,
    ObservationResponse,
    RelationResponse,
)
from basic_memory.schemas.search import SearchItemType, SearchResponse


async def create_entity(client) -> EntityResponse:
    data = {
        "title": "TestEntity",
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

    assert entity["title"] == data["title"]
    entity_type = entity.get("entity_type")
    assert entity_type == data["entity_type"]

    assert len(entity["observations"]) == 2

    create_response = EntityListResponse.model_validate(response_data)
    return create_response.entities[0]


async def add_observations(client, permalink: str) -> List[ObservationResponse]:
    response = await client.post(
        "/knowledge/observations",
        json={
            "permalink": permalink,
            "observations": [
                {"content": "First observation", "category": "tech"},
                {"content": "Second observation", "category": "note"},
            ],
            "context": "something special",
        },
    )
    # Verify observations were added
    assert response.status_code == 200
    data = response.json()

    obs_response = EntityResponse.model_validate(data)
    assert len(obs_response.observations) == 2
    return obs_response.observations


async def create_related_results(client) -> List[RelationResponse]:  # pyright: ignore [reportReturnType]
    # Create two entities to relate
    entities = [
        {"title": "SourceEntity", "entity_type": "test"},
        {"title": "TargetEntity", "entity_type": "test"},
    ]
    create_response = await client.post("/knowledge/entities", json={"entities": entities})
    assert create_response.status_code == 200
    created = create_response.json()["entities"]
    source_permalink = "source-entity"
    target_permalink = "target-entity"

    # Create relation between them
    response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {
                    "from_id": source_permalink,
                    "to_id": target_permalink,
                    "relation_type": "related_to",
                }
            ]
        },
    )

    # Verify relation
    assert response.status_code == 200
    data = response.json()

    relation_response = EntityListResponse.model_validate(data)
    assert len(relation_response.entities) == 1

    source_entity = relation_response.entities[0]

    assert len(source_entity.relations) == 1
    source_relation = source_entity.relations[0]
    assert source_relation.from_id == source_permalink
    assert source_relation.to_id == target_permalink

    return source_entity.relations


@pytest.mark.asyncio
async def test_create_entities(client: AsyncClient):
    """Should create entities successfully."""
    await create_entity(client)


@pytest.mark.asyncio
async def test_get_entity(client: AsyncClient):
    """Should retrieve an entity by path ID."""
    # First create an entity
    data = {"title": "TestEntity", "entity_type": "test"}
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    assert response.status_code == 200
    data = response.json()

    # Now get it by path
    permalink = data["entities"][0]["permalink"]
    response = await client.get(f"/knowledge/entities/{permalink}")

    # Verify retrieval
    assert response.status_code == 200
    entity = response.json()
    assert entity["title"] == "TestEntity"
    assert entity["entity_type"] == "test"
    assert entity["permalink"] == "test-entity"


@pytest.mark.asyncio
async def test_create_relations(client: AsyncClient):
    """Should create relations between entities."""
    await create_related_results(client)


@pytest.mark.asyncio
async def test_add_observations(client: AsyncClient):
    """Should add observations to an entity."""
    # Create an entity first
    data = {"title": "TestEntity", "entity_type": "test"}
    response = await client.post("/knowledge/entities", json={"entities": [data]})

    permalink = "test-entity"
    # Add observations
    await add_observations(client, permalink)

    # Verify observations appear in entity
    entity_response = await client.get(f"/knowledge/entities/{permalink}")
    entity = entity_response.json()
    assert len(entity["observations"]) == 2


@pytest.mark.asyncio
async def test_get_entities(client: AsyncClient):
    """Should open multiple entities by path IDs."""
    # Create a few entities with different names
    entities = [
        {"title": "AlphaTest", "entity_type": "test"},
        {"title": "BetaTest", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # Open nodes by path IDs
    response = await client.get(
        "/knowledge/entities?permalink=alpha-test&permalink=beta-test",
    )

    # Verify results
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 2

    entity_0 = data["entities"][0]
    assert entity_0["title"] == "AlphaTest"
    assert entity_0["entity_type"] == "test"
    assert entity_0["permalink"] == "alpha-test"

    entity_1 = data["entities"][1]
    assert entity_1["title"] == "BetaTest"
    assert entity_1["entity_type"] == "test"
    assert entity_1["permalink"] == "beta-test"


@pytest.mark.asyncio
async def test_delete_entity(client: AsyncClient):
    """Test DELETE /knowledge/entities with path ID."""
    # Create test entity
    entity_data = {"title": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})

    # Test deletion
    response = await client.post(
        "/knowledge/entities/delete", json={"permalinks": ["test/TestEntity"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify entity is gone
    permalink = quote("test/TestEntity")
    response = await client.get(f"/knowledge/entities/{permalink}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_bulk(client: AsyncClient):
    """Test bulk entity deletion using path IDs."""
    # Create test entities
    entities = [
        {"title": "Entity1", "entity_type": "test"},
        {"title": "Entity2", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": entities})

    # Test deletion
    response = await client.post(
        "/knowledge/entities/delete", json={"permalinks": ["Entity1", "Entity2"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify entities are gone
    for name in ["Entity1", "Entity2"]:
        permalink = quote(f"{name}")
        response = await client.get(f"/knowledge/entities/{permalink}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_with_observations(client, observation_repository):
    """Test cascading delete with observations."""
    # Create test entity and add observations
    entity_data = {"title": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})
    await add_observations(client, "test-entity")

    # Delete entity
    response = await client.post("/knowledge/entities/delete", json={"permalinks": ["test-entity"]})
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify observations are gone
    observations = await observation_repository.find_all()
    assert len(observations) == 0


@pytest.mark.asyncio
async def test_delete_observations(client, observation_repository):
    """Test deleting specific observations."""
    # Create entity and add observations
    entity_data = {"title": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})
    observations = await add_observations(client, "test-entity")  # adds 2

    # Delete specific observations
    request_data = {"permalink": "test-entity", "observations": [observations[0].content]}
    response = await client.post("/knowledge/observations/delete", json=request_data)
    assert response.status_code == 200
    data = response.json()

    del_response = EntityResponse.model_validate(data)
    assert len(del_response.observations) == 1
    assert del_response.observations[0].content == observations[1].content


@pytest.mark.asyncio
async def test_delete_relations(client, relation_repository):
    """Test deleting relations between entities."""
    relations = await create_related_results(client)
    assert len(relations) == 1
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

    del_response = EntityListResponse.model_validate(data)
    assert len(del_response.entities) == 2
    assert all(len(e.relations) == 0 for e in del_response.entities)


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(client: AsyncClient):
    """Test deleting a nonexistent entity by path ID."""
    response = await client.post(
        "/knowledge/entities/delete", json={"permalinks": ["non_existent"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}


@pytest.mark.asyncio
async def test_delete_nonexistent_observations(client: AsyncClient):
    """Test deleting nonexistent observations."""
    # Create test entity
    entity_data = {"title": "TestEntity", "entity_type": "test"}
    await client.post("/knowledge/entities", json={"entities": [entity_data]})

    request_data = {"permalink": "test-entity", "observations": ["Nonexistent observation"]}
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
                "from_id": "non_existent1",
                "to_id": "non_existent2",
                "relation_type": "nonexistent",
            }
        ]
    }
    response = await client.post("/knowledge/relations/delete", json=request_data)
    assert response.status_code == 200

    data = response.json()
    del_response = EntityListResponse.model_validate(data)
    assert del_response.entities == []


@pytest.mark.asyncio
async def test_full_knowledge_flow(client: AsyncClient):
    """Test complete knowledge graph flow with path IDs."""
    # 1. Create main entities
    main_entities = [
        {"title": "MainEntity", "entity_type": "test"},
        {"title": "NonEntity", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": main_entities})

    # 2. Create related entities
    related_results = [
        {"title": "RelatedOne", "entity_type": "test"},
        {"title": "RelatedTwo", "entity_type": "test"},
    ]
    await client.post("/knowledge/entities", json={"entities": related_results})

    # 3. Add relations
    relations_response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {
                    "from_id": "main-entity",
                    "to_id": "related-one",
                    "relation_type": "connects_to",
                },
                {
                    "from_id": "main-entity",
                    "to_id": "related-two",
                    "relation_type": "connects_to",
                },
            ]
        },
    )
    assert relations_response.status_code == 200
    relations_entities = relations_response.json()
    assert len(relations_entities["entities"]) == 1

    # 4. Add observations to main entity
    await client.post(
        "/knowledge/observations",
        json={
            "permalink": "main-entity",
            "observations": [
                {"content": "Connected to first related entity", "category": "tech"},
                {"content": "Connected to second related entity", "category": "note"},
            ],
            "context": "testing the flow",
        },
    )

    # 5. Verify full graph structure
    permalink = "main-entity"
    main_get = await client.get(f"/knowledge/entities/{permalink}")
    main_entity = main_get.json()

    # Check entity structure
    assert main_entity["title"] == "MainEntity"
    assert len(main_entity["observations"]) == 2
    assert len(main_entity["relations"]) == 2

    # 6. Search should find all related entities/relations/observations
    search = await client.post("/search/", json={"text": "Related"})
    matches = search.json()["results"]
    assert len(matches) == 6

    # 7. Delete main entity
    response = await client.post(
        "/knowledge/entities/delete", json={"permalinks": ["main-entity", "non-entity"]}
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify deletion
    permalink = "main-entity"
    response = await client.get(f"/knowledge/entities/{permalink}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_entity_indexing(client: AsyncClient):
    """Test entity creation includes search indexing."""
    data = {
        "title": "SearchTest",
        "entity_type": "test",
        "observations": ["Unique searchable observation"],
    }

    # Create entity
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    assert response.status_code == 200

    # Verify it's searchable
    search_response = await client.post(
        "/search/", json={"text": "search", "types": [SearchItemType.ENTITY.value]}
    )
    assert search_response.status_code == 200
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 1
    assert search_result.results[0].permalink == "search-test"
    assert search_result.results[0].type == SearchItemType.ENTITY.value


@pytest.mark.skip("observation info is not indexed yet")
@pytest.mark.asyncio
async def test_observation_update_indexing(client: AsyncClient):
    """Test observation changes are reflected in search."""
    # Create entity
    data = {
        "title": "TestEntity",
        "entity_type": "test",
        "observations": ["Initial observation"],
    }
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    assert response.status_code == 200
    entity = response.json()["entities"][0]

    # Add new observation
    await client.post(
        "/knowledge/observations",
        json={
            "permalink": entity["permalink"],
            "observations": [{"content": "Unique sphinx observation", "category": "tech"}],
        },
    )

    # Search for new observation
    search_response = await client.post(
        "/search/", json={"text": "sphinx", "types": [SearchItemType.ENTITY.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 1
    assert search_result.results[0].permalink == entity["permalink"]


@pytest.mark.asyncio
async def test_entity_delete_indexing(client: AsyncClient):
    """Test deleted entities are removed from search index."""
    data = {
        "title": "DeleteTest",
        "entity_type": "test",
        "observations": ["Searchable observation that should be removed"],
    }

    # Create entity
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    assert response.status_code == 200
    entity = response.json()["entities"][0]

    # Verify it's initially searchable
    search_response = await client.post(
        "/search/", json={"text": "delete", "types": [SearchItemType.ENTITY.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 1

    # Delete entity
    delete_response = await client.post(
        "/knowledge/entities/delete", json={"permalinks": [entity["permalink"]]}
    )
    assert delete_response.status_code == 200

    # Verify it's no longer searchable
    search_response = await client.post(
        "/search/", json={"text": "delete", "types": [SearchItemType.ENTITY.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 0


@pytest.mark.skip("relation info is not indexed yet")
@pytest.mark.asyncio
async def test_relation_indexing(client: AsyncClient):
    """Test relations are included in search index."""
    # Create entities
    entities = [
        {"title": "SourceTest", "entity_type": "test"},
        {"title": "TargetTest", "entity_type": "test"},
    ]
    create_response = await client.post("/knowledge/entities", json={"entities": entities})
    assert create_response.status_code == 200

    # Create relation with unique description
    response = await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {
                    "from_id": "source_test",
                    "to_id": "target_test",
                    "relation_type": "sphinx_relation",
                    "context": "Unique sphinx relation context",
                }
            ]
        },
    )
    assert response.status_code == 200

    # Search should find both entities through relation
    search_response = await client.post(
        "/search/", json={"text": "sphinx relation", "types": [SearchItemType.ENTITY.value]}
    )
    search_result = SearchResponse.model_validate(search_response.json())
    assert len(search_result.results) == 2  # Both source and target entities
    permalinks = {r.permalink for r in search_result.results}
    assert permalinks == {"source_test", "target_test"}


@pytest.mark.asyncio
async def test_update_entity_basic(client: AsyncClient):
    """Test basic entity field updates."""
    # Create initial entity
    data = {
        "title": "test",
        "entity_type": "test",
        "summary": "Initial description",
        "entity_metadata": {"status": "draft"},
    }
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    entity = response.json()["entities"][0]

    # Update basic fields
    update_data = {
        "title": "updated-test",
        "summary": "Updated description",
    }
    response = await client.put(f"/knowledge/entities/{entity['permalink']}", json=update_data)
    assert response.status_code == 200
    updated = response.json()

    # Verify updates
    assert updated["title"] == "updated-test"
    assert updated["summary"] == "Updated description"
    assert updated["entity_metadata"]["status"] == "draft"  # Preserved


@pytest.mark.skip("Skip until we can request content")
@pytest.mark.asyncio
async def test_update_entity_content(client: AsyncClient):
    """Test updating content for different entity types."""
    # Create a note entity
    note_data = {"title": "test-note", "entity_type": "note", "summary": "Test note"}
    response = await client.post("/knowledge/entities", json={"entities": [note_data]})
    note = response.json()["entities"][0]

    # Update note content
    new_content = "# Updated Note\n\nNew content."
    response = await client.put(
        f"/knowledge/entities/{note['permalink']}", json={"content": new_content}
    )
    assert response.status_code == 200
    updated = response.json()

    # Verify through get request to check file
    response = await client.get(f"/knowledge/entities/{updated['permalink']}?content=true")
    fetched = response.json()
    assert "# Updated Note" in fetched["content"]
    assert "New content" in fetched["content"]


@pytest.mark.asyncio
async def test_update_entity_type_conversion(client: AsyncClient):
    """Test converting between note and knowledge types."""
    # Create a note
    note_data = {
        "title": "test-note",
        "entity_type": "note",
        "summary": "Test note",
        "content": "# Test Note\n\nInitial content.",
    }
    response = await client.post("/knowledge/entities", json={"entities": [note_data]})
    note = response.json()["entities"][0]

    # Convert to knowledge type
    response = await client.put(
        f"/knowledge/entities/{note['permalink']}", json={"entity_type": "test"}
    )
    assert response.status_code == 200
    updated = response.json()

    # Verify conversion
    assert updated["entity_type"] == "test"

    # Get latest to verify file format
    response = await client.get(f"/knowledge/entities/{updated['permalink']}")
    knowledge = response.json()
    assert knowledge.get("content") is None


@pytest.mark.asyncio
async def test_update_entity_metadata(client: AsyncClient):
    """Test updating entity metadata."""
    # Create entity
    data = {"title": "test", "entity_type": "test", "entity_metadata": {"status": "draft"}}
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    entity = response.json()["entities"][0]

    # Update metadata
    update_data = {"entity_metadata": {"status": "final", "reviewed": True}}
    response = await client.put(f"/knowledge/entities/{entity['permalink']}", json=update_data)
    assert response.status_code == 200
    updated = response.json()

    # Verify metadata was merged, not replaced
    assert updated["entity_metadata"]["status"] == "final"
    assert updated["entity_metadata"]["reviewed"] is True


@pytest.mark.asyncio
async def test_update_entity_not_found(client: AsyncClient):
    """Test updating non-existent entity."""
    response = await client.put("/knowledge/entities/nonexistent", json={"title": "new-name"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_entity_search_index(client: AsyncClient):
    """Test search index is updated after entity changes."""
    # Create entity
    data = {"title": "test", "entity_type": "test", "summary": "Initial searchable content"}
    response = await client.post("/knowledge/entities", json={"entities": [data]})
    entity = response.json()["entities"][0]

    # Update with new searchable content
    update_data = {"summary": "Updated with unique sphinx marker"}
    response = await client.put(f"/knowledge/entities/{entity['permalink']}", json=update_data)
    assert response.status_code == 200

    # Search should find new content
    search_response = await client.post(
        "/search/", json={"text": "sphinx marker", "types": [SearchItemType.ENTITY.value]}
    )
    results = search_response.json()["results"]
    assert len(results) == 1
    assert results[0]["permalink"] == entity["permalink"]


@pytest.mark.asyncio
async def test_get_entity_with_relations(client: AsyncClient):
    """Test get response includes relations for both types."""
    # Create a note and knowledge entity
    note = await client.post(
        "/knowledge/entities",
        json={"entities": [{"title": "test-note", "entity_type": "note", "summary": "Test note"}]},
    )
    knowledge = await client.post(
        "/knowledge/entities",
        json={
            "entities": [
                {"title": "test-knowledge", "entity_type": "test", "summary": "Test knowledge"}
            ]
        },
    )

    # Add some relations between them
    await client.post(
        "/knowledge/relations",
        json={
            "relations": [
                {
                    "from_id": note.json()["entities"][0]["permalink"],
                    "to_id": knowledge.json()["entities"][0]["permalink"],
                    "relation_type": "references",
                }
            ]
        },
    )

    # Verify GET returns relations for both types
    note_response = await client.get(
        f"/knowledge/entities/{note.json()['entities'][0]['permalink']}"
    )
    knowledge_response = await client.get(
        f"/knowledge/entities/{knowledge.json()['entities'][0]['permalink']}"
    )

    assert len(note_response.json()["relations"]) == 1
    assert len(knowledge_response.json()["relations"]) == 1
