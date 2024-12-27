"""Knowledge graph models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint, text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basic_memory.models.base import Base
from basic_memory.models.documents import Document
from enum import Enum


class Entity(Base):
    """
    Core entity in the knowledge graph.

    Entities represent semantic nodes maintained by the AI layer. Each entity:
    - Has a unique numeric ID (database-generated)
    - Maps to a document file on disk (optional)
    - Maintains a checksum for change detection
    - Tracks both source document and semantic properties
    """

    __tablename__ = "entity"
    __table_args__ = (
        UniqueConstraint("entity_type", "name", name="uix_entity_type_name"),
        Index("ix_entity_type", "entity_type"),
        Index("ix_entity_doc_id", "doc_id"),
        Index("ix_entity_created_at", "created_at"),  # For timeline queries
        Index("ix_entity_updated_at", "updated_at")   # For timeline queries
    )

    # Core identity
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str] = mapped_column(String)
    # Normalized path for URIs
    # (entity_type, path_id) are unique
    path_id: Mapped[str] = mapped_column(String, index=True)
    # Actual filesystem relative path
    file_path: Mapped[str] = mapped_column(String, unique=True, index=True)

    # Content and validation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Metadata and tracking
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )

    # Relations
    doc_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    observations = relationship(
        "Observation", back_populates="entity", cascade="all, delete-orphan"
    )
    from_relations = relationship(
        "Relation",
        back_populates="from_entity",
        foreign_keys="[Relation.from_id]",
        cascade="all, delete-orphan",
    )
    to_relations = relationship(
        "Relation",
        back_populates="to_entity",
        foreign_keys="[Relation.to_id]",
        cascade="all, delete-orphan",
    )
    document: Mapped[Optional[Document]] = relationship(Document, back_populates="entities")

    @property
    def relations(self):
        return self.to_relations + self.from_relations

    def __repr__(self) -> str:
        return f"Entity(id={self.id}, name='{self.name}', type='{self.entity_type}')"


class ObservationCategory(str, Enum):
    TECH = "tech"
    DESIGN = "design"
    FEATURE = "feature"
    NOTE = "note"
    ISSUE = "issue"
    TODO = "todo"

class Observation(Base):
    """
    An observation about an entity.

    Observations are atomic facts or notes about an entity.
    """

    __tablename__ = "observation"
    __table_args__ = (
        Index("ix_observation_entity_id", "entity_id"), # Add FK index
        Index("ix_observation_category", "category"),    # Add category index
        Index("ix_observation_created_at", "created_at"),  # For timeline queries
        Index("ix_observation_updated_at", "updated_at"),  # For timeline queries
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("entity.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ObservationCategory.NOTE.value,
        server_default=ObservationCategory.NOTE.value
    )
    context: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )

    # Relationships
    entity = relationship("Entity", back_populates="observations")

    def __repr__(self) -> str:
        return f"Observation(id={self.id}, entity_id={self.entity_id}, content='{self.content}')"


class Relation(Base):
    """
    A directed relation between two entities.
    """

    __tablename__ = "relation"
    __table_args__ = (
        UniqueConstraint("from_id", "to_id", "relation_type", name="uix_relation"),
        Index("ix_relation_type", "relation_type"),
        Index("ix_relation_from_id", "from_id"),  # Add FK indexes
        Index("ix_relation_to_id", "to_id"),
        Index("ix_relation_created_at", "created_at"),  # For timeline queries
        Index("ix_relation_updated_at", "updated_at"),  # For timeline queries
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_id: Mapped[int] = mapped_column(Integer, ForeignKey("entity.id", ondelete="CASCADE"))
    to_id: Mapped[int] = mapped_column(Integer, ForeignKey("entity.id", ondelete="CASCADE"))
    relation_type: Mapped[str] = mapped_column(String)
    context: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )

    # Relationships
    from_entity = relationship("Entity", foreign_keys=[from_id], back_populates="from_relations")
    to_entity = relationship("Entity", foreign_keys=[to_id], back_populates="to_relations")

    def __repr__(self) -> str:
        return f"Relation(id={self.id}, from_id={self.from_id}, to_id={self.to_id}, type='{self.relation_type}')"
