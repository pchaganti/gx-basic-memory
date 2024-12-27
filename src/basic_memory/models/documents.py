"""Models for storing documents."""

from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from basic_memory.db import Base


class Document(Base):
    """Document model."""
    __tablename__ = "document"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    # Normalized path for URIs
    path_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    # Actual filesystem relative path
    file_path: Mapped[str] = mapped_column(String, unique=True, index=True)  
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    doc_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True,
        default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    @property
    def normalized_path(self) -> str:
        """Get path for URI routing."""
        return self.path_id
