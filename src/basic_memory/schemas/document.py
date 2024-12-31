"""Document related schemas."""
from typing import Dict, Optional

from pydantic import BaseModel, Field
from basic_memory.schemas.request import DocumentPathId


class CreateDocumentRequest(BaseModel):
    """Request to create a new document."""
    path_id: DocumentPathId = Field(..., description="Path to the document")
    content: str = Field(..., description="Document content")
    doc_metadata: Optional[Dict] = Field(default=None, description="Optional metadata")


class DocumentUpdate(BaseModel):
    """Request to update a document."""
    content: Optional[str] = None
    doc_metadata: Optional[Dict] = None