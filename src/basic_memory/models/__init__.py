"""Models package for basic-memory."""

import basic_memory
from basic_memory.models.base import Base
from basic_memory.models.knowledge import Entity, Observation, Relation, ObservationCategory

SCHEMA_VERSION = basic_memory.__version__ + "-" + "003"

__all__ = [
    "Base",
    "Entity",
    "Observation",
    "ObservationCategory",
    "Relation",
]
