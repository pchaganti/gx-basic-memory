"""Document model for tracking files in the knowledge base."""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basic_memory.models.base import Base


class Document(Base):
    """
    Tracks documents in the filesystem.

    Documents files are the source of truth for document content, while this table
    provides indexing and metadata storage. Like git, the filesystem
    is the real source of truth.
    """

    __tablename__ = "document"
    __table_args__ = (
        Index("ix_document_created_at", "created_at"),
        Index("ix_document_updated_at", "updated_at")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Normalized path for URIs
    # path_id is unique for documents
    path_id: Mapped[str] = mapped_column(String, unique=True,index=True)
    # Actual filesystem relative path
    file_path: Mapped[str] = mapped_column(String, unique=True, index=True)

    checksum: Mapped[str] = mapped_column(String, nullable=True)
    doc_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # renamed from metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )

    # Relationships
    entities: Mapped[List["Entity"]] = relationship(  # pyright: ignore [reportUndefinedVariable]  # noqa: F821
        "Entity", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Document(id={self.id}, path='{self.path}',  checksum='{self.checksum}', created_at='{self.created_at}', updated_at='{self.updated_at}')"
