"""Database configuration and initialization for basic-memory."""
from enum import Enum
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.pool import StaticPool

from basic_memory.models import Base

class DatabaseType(Enum):
    """Types of database configurations."""
    MEMORY = "memory"      # In-memory SQLite for testing
    FILESYSTEM = "file"    # File-based SQLite for projects

def get_database_url(db_type: DatabaseType, project_path: Optional[Path] = None) -> str:
    """
    Get database URL based on type and optional project path.
    
    Args:
        db_type: Type of database to configure
        project_path: Project directory for file-based DBs (required if type is FILESYSTEM)
        
    Returns:
        Database URL string
    
    Raises:
        ValueError: If project_path is required but not provided
    """
    match db_type:
        case DatabaseType.MEMORY:
            return "sqlite+aiosqlite:///:memory:"
            
        case DatabaseType.FILESYSTEM:
            if not project_path:
                raise ValueError("project_path required for filesystem database")
                
            # Ensure data directory exists
            data_dir = project_path / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            db_path = data_dir / "memory.db"
            return f"sqlite+aiosqlite:///{db_path}"

async def init_database(url: str, echo: bool = False) -> AsyncEngine:
    """
    Initialize database with schema.
    
    Args:
        url: Database URL
        echo: Whether to echo SQL statements
        
    Returns:
        Configured async engine
    """
    # Configure engine based on URL
    connect_args = {"check_same_thread": False}
    if url == "sqlite+aiosqlite:///:memory:":
        engine = create_async_engine(
            url,
            echo=echo,
            poolclass=StaticPool,  # Single connection for in-memory
            connect_args=connect_args
        )
    else:
        engine = create_async_engine(
            url,
            echo=echo,
            connect_args=connect_args
        )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    return engine

@asynccontextmanager
async def get_session(engine: AsyncEngine):
    """
    Get database session with proper lifecycle management.
    
    Args:
        engine: Async engine to create session from
        
    Yields:
        AsyncSession configured for engine
    """
    # Create session factory
    async_session = async_sessionmaker(
        engine,
        expire_on_commit=False
    )
    
    # Create and yield session
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

async def dispose_database(engine: AsyncEngine):
    """
    Clean up database engine.
    
    Args:
        engine: Engine to dispose
    """
    await engine.dispose()