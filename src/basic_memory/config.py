"""Configuration management for basic-memory."""
from pathlib import Path
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

DATABASE_NAME = "memory.db"

class ProjectConfig(BaseSettings):
    """Configuration for a specific basic-memory project."""
    name: str = Field(default="default")
    path: Path = Field(
        default_factory=lambda: Path.home() / ".basic-memory" / "projects" / "default",
        description="Path to project files"
    )
    
    model_config = SettingsConfigDict(
        env_prefix='BASIC_MEMORY_',  # env vars like BASIC_MEMORY_DB_URL
        extra='ignore',
        env_file=".env",
        env_file_encoding="utf-8"
    )

    @property
    def database_url(self) -> str:
        """Get SQLite database URL based on project path."""
        db_path = self.path / "data" / DATABASE_NAME
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"
    
    @field_validator('path')
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure project path exists."""
        if not v.exists():
            v.mkdir(parents=True)
        return v

@asynccontextmanager
async def get_testing_services(
    config: ProjectConfig,
    memory_service: Optional["MemoryService"] = None
) -> AsyncGenerator["MemoryService", None]:
    """Get services for testing with optional pre-configured service.
    
    Args:
        config: Project configuration
        memory_service: Optional pre-configured service for testing
        
    Yields:
        Configured MemoryService instance with proper lifecycle management
    """
    if memory_service:
        yield memory_service
        return

    from basic_memory.deps import get_project_services
    async with get_project_services(config.path) as service:
        yield service