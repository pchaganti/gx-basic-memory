"""Tests for the MCP server implementation using FastAPI TestClient."""

import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from basic_memory.api.app import app as fastapi_app
from basic_memory.deps import get_project_config, get_engine_factory


@pytest_asyncio.fixture
def app(test_config, engine_session_factory) -> FastAPI:
    """Create test FastAPI application."""
    app = fastapi_app
    app.dependency_overrides[get_project_config] = lambda: test_config
    app.dependency_overrides[get_engine_factory] = lambda: engine_session_factory
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """Create test client that both MCP and tests will use."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
def test_entity_data():
    """Sample data for creating a test entity."""
    return {
        "entities": [
            {
                "name": "Test Entity",
                "entity_type": "test",
                "description": "",  # Empty string instead of None
                "observations": ["This is a test observation"],
            }
        ]
    }


@pytest_asyncio.fixture
def test_directory_entity_data():
    """Real data that caused failure in the tool."""
    return {
        "entities": [
            {
                "name": "Directory Organization",
                "entity_type": "memory",
                "description": "Implemented filesystem organization by entity type",
                "observations": [
                    "Files are now organized by type using directories like entities/project/basic_memory",
                    "Entity IDs match filesystem paths for better mental model",
                    "Fixed path handling bugs by adding consistent get_entity_path helper",
                ],
            }
        ]
    }
