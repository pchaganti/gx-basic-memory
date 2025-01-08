"""Test activity router."""

import pytest
from httpx import AsyncClient

from basic_memory.schemas.activity import ActivityType


@pytest.mark.anyio
async def test_get_recent_activity(client: AsyncClient):
    """Test getting recent activity."""
    # Get initial activity
    response = await client.get("/activity/recent")
    assert response.status_code == 200

    # Parse response
    data = response.json()
    assert "changes" in data
    assert "summary" in data
    assert "timeframe" in data
    assert data["timeframe"] == "1d"  # Default timeframe


@pytest.mark.anyio
async def test_get_recent_activity_with_filters(client: AsyncClient):
    """Test getting recent activity with filters."""
    # Get activity with filters
    response = await client.get(
        "/activity/recent",
        params={
            "timeframe": "1h",
            "activity_types": [ActivityType.ENTITY.value],
            "include_content": False
        }
    )
    assert response.status_code == 200

    # Parse response
    data = response.json()
    assert data["timeframe"] == "1h"
    
    # Verify all changes are document type
    for change in data["changes"]:
        assert change["activity_type"] == ActivityType.ENTITY.value
        assert change["content"] is None  # Content excluded