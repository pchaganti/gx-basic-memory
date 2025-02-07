"""Base model class for SQLAlchemy models."""
from sqlalchemy import String, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models"""
    pass


class SchemaVersion(Base):
    """Track database schema version."""

    __tablename__ = "schema_version"

    # Only one row will exist
    version: Mapped[str] = mapped_column(String, primary_key=True)

    def __repr__(self) -> str:
        return f"SchemaVersion(version='{self.version}')"