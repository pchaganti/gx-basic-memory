"""Tests for repository behavior using raw SQL."""
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.anyio


async def test_sqlite_default_timestamp(session):
    """Test SQLite's handling of default CURRENT_TIMESTAMP."""
    # First create test entity
    await session.execute(
        text("""
        INSERT INTO entity (id, name, entity_type, description)
        VALUES ('test/test_entity', 'Test', 'test', 'Test description')
        """)
    )
    await session.commit()

    # Now try to insert observation with no timestamp
    await session.execute(
        text("""
        INSERT INTO observation (entity_id, content)
        VALUES ('test/test_entity', 'Test observation')
        """)
    )
    await session.commit()

    # Verify timestamp was set
    result = await session.execute(
        text("SELECT created_at FROM observation WHERE entity_id = 'test/test_entity'")
    )
    observation = result.fetchone()
    assert observation is not None
    assert observation.created_at is not None