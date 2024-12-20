"""Service layer exceptions and imports."""


class ServiceError(Exception):
    """Base exception for service errors"""

    pass


class DatabaseSyncError(ServiceError):
    """Raised when database sync fails"""

    pass


class RelationError(ServiceError):
    """Base exception for relation-specific errors"""

    pass


from .entity_service import EntityService
from .observation_service import ObservationService
from .relation_service import RelationService

__all__ = [
    "ServiceError",
    "DatabaseSyncError",
    "RelationError",
    "EntityService",
    "ObservationService",
    "RelationService",
]
