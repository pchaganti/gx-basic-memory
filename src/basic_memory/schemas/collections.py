"""Collection response schemas for Basic Memory."""

from typing import Dict, List

from pydantic import BaseModel, Field

from basic_memory.schemas.response import (
    EntityResponse,
    DocumentCreateResponse
)


class EntityMap(BaseModel):
    """Map of entity path_ids to their data."""
    
    entities: Dict[str, EntityResponse] = Field(
        description="Map of path_ids to entity data"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "description": "Map of entity path_ids to their complete data"
        }


class DocumentList(BaseModel):
    """List of documents with metadata."""
    
    documents: List[DocumentCreateResponse] = Field(
        description="List of documents with their metadata"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "description": "List of documents in the knowledge base"
        }


class DeleteResult(BaseModel):
    """Result of a delete operation."""
    
    deleted: bool = Field(
        description="Whether the deletion was successful"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "description": "Result indicating if deletion succeeded"
        }