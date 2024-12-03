from datetime import datetime, UTC
from typing import List
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Entity(AsyncAttrs, Base):
    """
    Core entity in the knowledge graph.

    Entities are the primary nodes in the knowledge graph. Each entity has:
    - A unique identifier
    - A name
    - An entity type (e.g., "person", "organization", "event")
    - A description
    - A list of observations
    - References (optional
    """
    __tablename__ = "entities"

    # Primary key is a UUID string for compatibility with markdown IDs
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC)
    )

    # Relationships
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="entity",
        cascade="all, delete-orphan"
    )
    outgoing_relations: Mapped[List["Relation"]] = relationship(
        "Relation",
        foreign_keys="[Relation.from_id]",
        back_populates="from_entity",
        cascade="all, delete-orphan"
    )
    incoming_relations: Mapped[List["Relation"]] = relationship(
        "Relation",
        foreign_keys="[Relation.to_id]",
        back_populates="to_entity",
        cascade="all, delete-orphan"
    )


class Observation(AsyncAttrs, Base):
    """
    Observations are discrete pieces of information about an entity. They are:
    - Stored as strings
    - Attached to specific entities
    - Can be added or removed independently
    - Should be atomic (one fact per observation)
    """
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True
    )
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC)
    )
    context: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="observations"
    )


class Relation(AsyncAttrs, Base):
    """
    Relations define directed connections between entities.
    They are always stored in active voice and describe how entities interact or relate to each other.
    """
    __tablename__ = "relations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True
    )
    to_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True
    )
    relation_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC)
    )
    context: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    from_entity: Mapped[Entity] = relationship(
        "Entity",
        foreign_keys=[from_id],
        back_populates="outgoing_relations"
    )
    to_entity: Mapped[Entity] = relationship(
        "Entity",
        foreign_keys=[to_id],
        back_populates="incoming_relations"
    )