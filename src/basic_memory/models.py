"""Database models for basic-memory."""
from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, TypeDecorator, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class UTCDateTime(TypeDecorator):
    """Automatically handle UTC timezone for datetime columns"""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value
        return value

    def process_result_value(self, value: Optional[datetime], dialect):
        if value is not None:
            return value.replace(tzinfo=UTC)
        return value


def utc_now() -> datetime:
    """Helper to get current UTC time"""
    return datetime.now(UTC)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models"""
    pass


class Entity(Base):
    """
    Core entity in the knowledge graph.

    Entities are the primary nodes in the knowledge graph. Each entity has:
    - A unique identifier (text, for filesystem references)
    - A name
    - An entity type (e.g., "person", "organization", "event")
    - A description (optional)
    - A list of observations
    """
    __tablename__ = "entity"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=utc_now
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

    def __repr__(self) -> str:
        return f"Entity(id='{self.id}', name='{self.name}', type='{self.entity_type}')"


class Observation(Base):
    """
    Observations are discrete pieces of information about an entity. They are:
    - Stored as strings
    - Attached to specific entities
    - Can be added or removed independently
    - Should be atomic (one fact per observation)
    """
    __tablename__ = "observation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[str] = mapped_column(  # Reference Entity.id which is text
        String, 
        ForeignKey("entity.id", ondelete="CASCADE"),
        index=True
    )
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    context: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="observations"
    )

    def __repr__(self) -> str:
        content = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Observation(id={self.id}, entity='{self.entity_id}', content='{content}')"


class Relation(Base):
    """
    Relations define directed connections between entities.
    They are always stored in active voice and describe how entities interact or relate to each other.
    """
    __tablename__ = "relation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_id: Mapped[str] = mapped_column(  # Reference Entity.id which is text
        String,
        ForeignKey("entity.id", ondelete="CASCADE"),
        index=True
    )
    to_id: Mapped[str] = mapped_column(  # Reference Entity.id which is text
        String,
        ForeignKey("entity.id", ondelete="CASCADE"),
        index=True
    )
    relation_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=text('CURRENT_TIMESTAMP')
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

    def __repr__(self) -> str:
        return f"Relation(id={self.id}, from='{self.from_id}', type='{self.relation_type}', to='{self.to_id}')"