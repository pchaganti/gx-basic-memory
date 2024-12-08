"""Configuration management for basic-memory."""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class ProjectConfig(BaseSettings):
    """Configuration for a specific basic-memory project."""
    name: str = Field(default="default")
    db_url: str = Field(
        default="sqlite+aiosqlite:///:memory:",
        description="Database URL - defaults to in-memory SQLite"
    )
    path: Path = Field(
        default_factory=lambda: Path.home() / ".basic-memory" / "projects" / "default",
        description="Path to project files"
    )
    
    model_config = SettingsConfigDict(
        env_prefix='BASIC_MEMORY_',  # env vars like BASIC_MEMORY_DB_URL
        extra='forbid'
    )
    
    @field_validator('path')
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure project path exists."""
        if not v.exists():
            v.mkdir(parents=True)
        return v

async def create_project_services(
    config: ProjectConfig,
    memory_service: Optional["MemoryService"] = None  # Forward ref since this is used in mcp
) -> "MemoryService":
    """Create all services needed for a project.
    
    Args:
        config: Project configuration
        memory_service: Optional pre-configured service for testing
        
    Returns:
        Configured MemoryService instance
    """
    if memory_service:
        return memory_service
        
    from basic_memory.db import init_database, get_session
    from basic_memory.deps import (
        get_entity_repo, get_observation_repo, get_relation_repo,
        get_entity_service, get_observation_service, get_relation_service,
        get_memory_service
    )
    
    engine = await init_database(config.db_url)
    async with get_session(engine) as session:
        entity_repo = await get_entity_repo(session)
        observation_repo = await get_observation_repo(session)
        relation_repo = await get_relation_repo(session)
        
        entity_service = await get_entity_service(config.path, entity_repo)
        observation_service = await get_observation_service(config.path, observation_repo)
        relation_service = await get_relation_service(config.path, relation_repo)
        
        return await get_memory_service(
            config.path,
            entity_service,
            relation_service, 
            observation_service
        )