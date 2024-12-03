from pathlib import Path
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

"""
This module sets up the configuration for the asynchronous SQLAlchemy engine and session factory,
adapted for SQLite with aiosqlite driver.

Objects:
    engine: An asynchronous database engine configured for SQLite
    async_sessionmaker: A session factory that creates new instances of AsyncSession using the engine

Usage:
    The async_sessionmaker can be imported and used to create new AsyncSession instances
    for database operations.

Example:
    ```python
    from basic_memory.core.db import async_sessionmaker

    async def get_entities():
        async with async_sessionmaker() as session:
            result = await session.execute("SELECT * FROM entities")
            entities = result.fetchall()
            return entities
    ```
"""

def get_database_url(project_name: str) -> str:
    """
    Construct the SQLite database URL for a given project.

    Args:
        project_name: Name of the project to get database URL for

    Returns:
        str: Complete aiosqlite URL for the project database
    """
    # Create data directory if it doesn't exist
    data_dir = Path.home() / ".basic-memory" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Construct database path
    db_path = data_dir / f"{project_name}.db"

    # Return aiosqlite URL
    return f"sqlite+aiosqlite:///{db_path}"

class DatabaseConnection:
    """
    Manages database connection and session factory for a specific project.
    """

    def __init__(self, project_name: str):
        """
        Initialize database connection for a project.

        Args:
            project_name: Name of the project to connect to
        """
        self.db_url = get_database_url(project_name)
        self.engine = create_async_engine(
            self.db_url,
            echo=True,  # Log SQL queries for debugging
            connect_args={"check_same_thread": False}  # Required for SQLite
        )
        self.async_sessionmaker = async_sessionmaker(
            self.engine,
            expire_on_commit=False
        )

    async def dispose(self):
        """
        Clean up database connection and resources.
        """
        await self.engine.dispose()

# Global connection state - initialized when setting active project
current_connection: DatabaseConnection | None = None

def init_connection(project_name: str):
    """
    Initialize or switch the active database connection.

    Args:
        project_name: Name of the project to connect to
    """
    global current_connection

    # Clean up existing connection if any
    if current_connection is not None:
        import asyncio
        asyncio.create_task(current_connection.dispose())

    # Create new connection
    current_connection = DatabaseConnection(project_name)

    return current_connection

def get_sessionmaker() -> async_sessionmaker:
    """
    Get the active session maker.

    Returns:
        AsyncSessionMaker for the current project's database

    Raises:
        RuntimeError: If no project connection has been initialized
    """
    if current_connection is None:
        raise RuntimeError(
            "No active database connection. Call init_connection() first."
        )
    return current_connection.async_sessionmaker