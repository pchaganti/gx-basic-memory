"""Tests for knowledge graph API endpoints."""
from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from icecream import ic
from loguru import logger

from basic_memory.models import Entity
from basic_memory.deps import get_project_services


@pytest_asyncio.fixture
def app(memory_service_mock: AsyncMock) -> FastAPI:
    """Create FastAPI test application."""
    # Lazy import router to avoid app startup issues
    from basic_memory.api.routers.knowledge import router

    app = FastAPI()
    app.include_router(router)

    # Override service dependency with mock
    async def memory_service_override(project_path: Path):
        yield memory_service_mock

    app.dependency_overrides[get_project_services] = memory_service_override
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create client using ASGI transport - same as CLI will use."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
def memory_service_mock() -> AsyncMock:
    """Create service mock."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_entities(client: AsyncClient, memory_service_mock):
    """Should create entities successfully."""
    # Setup mock
    entity = Entity(id="test-1", name="Test Entity", entity_type="test")
    memory_service_mock.create_entities.return_value = [entity]

    # Make request like a real client would
    response = await client.post("/knowledge/entities", json={
        "entities": [{
            "name": "Test Entity",
            "entity_type": "test"
        }]
    })

    logger.debug(ic(response.content))


    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 1
    assert data["entities"][0]["id"] == "test-1"

    # Verify service called
    memory_service_mock.create_entities.assert_called_once()