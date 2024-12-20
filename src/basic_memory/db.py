import asyncio
from contextlib import asynccontextmanager
from enum import Enum, auto
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
    async_scoped_session,
)


class DatabaseType(Enum):
    """Types of supported databases."""

    MEMORY = auto()
    FILESYSTEM = auto()

    @classmethod
    def get_db_path(cls, project_path: Path, db_type: "DatabaseType") -> Path:
        """Get database path based on type."""
        if db_type == cls.MEMORY:
            return Path(":memory:")
        else:
            return project_path / "data" / "memory.db"

    @classmethod
    def get_db_url(cls, db_path: Path) -> str:
        """Get SQLAlchemy URL for database path."""
        if str(db_path) == ":memory:":
            return "sqlite+aiosqlite://"
        return f"sqlite+aiosqlite:///{db_path}"


def get_scoped_session_factory(
    session_maker: async_sessionmaker[AsyncSession],
) -> async_scoped_session:
    """Create a scoped session factory scoped to current task."""
    return async_scoped_session(session_maker, scopefunc=asyncio.current_task)


# @asynccontextmanager
# async def session(
#     session_factory: async_sessionmaker[AsyncSession],
# ) -> AsyncGenerator[AsyncSession, None]:
#     """
#     Get database session with proper lifecycle management.
#
#     Args:
#         session_factory: Async session factory to create session from
#
#     Yields:
#         AsyncSession configured for engine
#     """
#     session = session_factory()
#     try:
#         await session.execute(text("PRAGMA foreign_keys=ON"))
#         yield session
#         await session.commit()
#     except Exception:
#         await session.rollback()
#         raise
#     finally:
#         await session.close()
#


@asynccontextmanager
async def scoped_session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a scoped session with proper lifecycle management.

    Args:
        session_maker: Session maker to create scoped sessions from
    """
    factory = get_scoped_session_factory(session_maker)
    session = factory()
    try:
        await session.execute(text("PRAGMA foreign_keys=ON"))
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        await factory.remove()


@asynccontextmanager
async def engine_session_factory(
    project_path: Path,
    db_type: DatabaseType = DatabaseType.FILESYSTEM,
) -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    """Create engine and session factory."""
    db_path = DatabaseType.get_db_path(project_path, db_type)
    db_url = DatabaseType.get_db_url(db_path)
    engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with scoped_session(factory) as db_session:
            # Initialize database
            await db_session.execute(text("PRAGMA foreign_keys=ON"))

        yield engine, factory
    finally:
        await engine.dispose()
