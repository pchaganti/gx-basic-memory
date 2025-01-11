"""Configuration management for basic-memory."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DATABASE_NAME = "memory.db"
DATA_DIR_NAME = ".basic-memory"


class ProjectConfig(BaseSettings):
    """Configuration for a specific basic-memory project."""

    # Default to ~/basic-memory but allow override with env var: BASIC_MEMORY_HOME
    home: Path = Field(
        default_factory=lambda: Path.home() / "basic-memory",
        description="Base path for basic-memory files",
    )

    model_config = SettingsConfigDict(
        env_prefix="BASIC_MEMORY_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


    @property
    def database_path(self) -> Path:
        """Get SQLite database path."""
        return self.home / DATA_DIR_NAME / DATABASE_NAME

    @field_validator("home")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure project path exists."""
        if not v.exists():
            v.mkdir(parents=True)
        return v


# Load project config
config = ProjectConfig()
