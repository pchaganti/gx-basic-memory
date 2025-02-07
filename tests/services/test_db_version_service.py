"""Tests for DatabaseManagementService."""

from pathlib import Path
from datetime import datetime, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from basic_memory import db
from basic_memory.db import DatabaseType
from basic_memory.models import Base
from basic_memory.services.db_version_service import DbVersionService


# special version of the engine factory with a filesystem db type
@pytest_asyncio.fixture(scope="function")
async def engine_factory(
    test_config,
) -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    """Create engine and session factory using in-memory SQLite database."""
    async with db.engine_session_factory(
        db_path=test_config.database_path, db_type=DatabaseType.FILESYSTEM
    ) as (engine, session_maker):
        # Initialize database
        async with db.scoped_session(session_maker) as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))
            conn = await session.connection()
            await conn.run_sync(Base.metadata.create_all)

        yield engine, session_maker

@pytest.mark.asyncio
async def test_check_db_initializes_new_db(db_version_service: DbVersionService, session_maker):
    """Test that check_db initializes new database."""
    # Ensure DB doesn't exist
    if Path(db_version_service.db_path).exists():
        Path(db_version_service.db_path).unlink()

    # Check DB - should initialize
    assert await db_version_service.check_db()

    # Verify schema version was set
    async with db.scoped_session(session_maker) as session:
        version = await db.get_schema_version(session)
        assert version == db.SCHEMA_VERSION


@pytest.mark.asyncio
async def test_check_db_rebuilds_on_version_mismatch(
    db_version_service: DbVersionService, session_maker
):
    """Test that check_db rebuilds DB when schema version doesn't match."""
    # Initialize DB first
    assert await db_version_service.check_db()

    # Set old version
    async with db.scoped_session(session_maker) as session:
        await db.set_schema_version(session, "000")

    # Check DB - should rebuild
    assert await db_version_service.check_db()

    # Verify version was updated
    async with db.scoped_session(session_maker) as session:
        version = await db.get_schema_version(session)
        assert version == db.SCHEMA_VERSION


@pytest.mark.asyncio
async def test_backup_creates_timestamped_file(
    db_version_service: DbVersionService,
):
    """Test that backup creates properly named backup file."""
    # Create dummy DB file
    db_version_service.db_path.write_text("test content")

    # Create backup
    backup_path = await db_version_service.create_backup()

    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.suffix == ".backup"
    assert datetime.now().strftime("%Y%m%d") in backup_path.name


