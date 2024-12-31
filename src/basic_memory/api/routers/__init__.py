"""API routers."""

from . import knowledge_router as knowledge
from . import documents_router as documents
from . import discovery_router as discovery

__all__ = ["knowledge", "documents", "discovery"]
