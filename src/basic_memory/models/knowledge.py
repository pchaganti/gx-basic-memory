"""Models for storing knowledge entities and their relationships."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from basic_memory.db import Base


class Entity(Base):
    """Entity model."""
    __tablename__ = "entity"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str] = mapped_column(String)
    # Normalized path for URIs
    path_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    # Actual filesystem relative path
    file_path: Mapped[str] = mapped_column(String, unique=True, index=True)  
    description: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)

    # Relations
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="entity",
        cascade="all, delete-orphan"
    )
    outbound_relations: Mapped[List["Relation"]] = relationship(
        "Relation",
        back_populates="from_entity",
        foreign_keys="[Relation.from_id]",
        cascade="all, delete-orphan"
    )
    inbound_relations: Mapped[List["Relation"]] = relationship(
        "Relation",
        back_populates="to_entity",
        foreign_keys="[Relation.to_id]",
        cascade="all, delete-orphan"
    )
    document: Mapped[Optional["Document"]] = relationship("Document")

    @property
    def normalized_path(self) -> str:
        """Get path for URI routing."""
        return self.path_id


class Observation(Base):
    """Model for entity observations."""
    __tablename__ = "observation"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    content: Mapped[str] = mapped_column(String)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relations
    entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="observations"
    )


class Relation(Base):
    """Model for entity relationships."""
    __tablename__ = "relation"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    from_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    to_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    relation_type: Mapped[str] = mapped_column(String)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relations
    from_entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="outbound_relations",
        foreign_keys=[from_id]
    )
    to_entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="inbound_relations",
        foreign_keys=[to_id]
    )