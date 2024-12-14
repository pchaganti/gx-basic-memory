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

from basic_memory.deps import get_project_config, get_engine
from basic_memory.models import Entity


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
    assert data["entities"][0]["id"] == "test/test_entity"
