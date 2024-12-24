"""Configuration management for basic-memory."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DATABASE_NAME = "memory.db"
KNOWLEDGE_DIR_NAME = "knowledge"
DOCUMENTS_DIR_NAME = "documents"
DATA_DIR_NAME = "data"


class ProjectConfig(BaseSettings):
    """Configuration for a specific basic-memory project."""

    name: str = Field(default="default")
    path: Path = Field(
        default_factory=lambda: Path.home() / ".basic-memory" / "projects" / "default",
        description="Path to project files",
    )

    model_config = SettingsConfigDict(
        env_prefix="BASIC_MEMORY_",  # env vars like BASIC_MEMORY_DB_URL
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def knowledge_dir(self) -> Path:
        """Get knowledge directory path based on project path."""
        knowledge_path = self.path / KNOWLEDGE_DIR_NAME
        knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        return knowledge_path

    @property
    def documents_dir(self) -> Path:
        """Get documents directory path based on project path."""
        documents_path = self.path / DOCUMENTS_DIR_NAME
        documents_path.parent.mkdir(parents=True, exist_ok=True)
        return documents_path

    @property
    def database_path(self) -> Path:
        """Get SQLite database URL based on project path."""
        db_path = self.path / DATA_DIR_NAME / DATABASE_NAME
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    @field_validator("path")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure project path exists."""
        if not v.exists():
            v.mkdir(parents=True)
        return v


# Load project config
config = ProjectConfig()
