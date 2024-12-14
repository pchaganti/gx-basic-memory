"""FastAPI dependency functions."""
from typing import Annotated

from fastapi import Depends

from basic_memory.config import project_path
from basic_memory.deps import get_project_services
from basic_memory.services import MemoryService

MemoryServiceDep = Annotated[MemoryService, Depends(get_project_services(project_path))]

