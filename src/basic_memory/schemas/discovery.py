"""Schemas for knowledge discovery and analytics endpoints."""

from typing import List
from pydantic import BaseModel


class EntityTypeList(BaseModel):
    """List of unique entity types in the system."""
    types: List[str]


class ObservationCategoryList(BaseModel):
    """List of unique observation categories in the system."""
    categories: List[str]
