"""Routes for getting entity content."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from basic_memory.deps import EntityRepositoryDep, ProjectConfigDep

router = APIRouter(prefix="/resource", tags=["resources"])


@router.get("/{permalink:path}")
async def get_resource_content(
    config: ProjectConfigDep,
    entity_repository: EntityRepositoryDep,
    permalink: str,
) -> FileResponse:
    """Get resource content by permalink."""
    logger.debug(f"Getting content for permalink: {permalink}")

    # Find entity by permalink
    entity = await entity_repository.get_by_permalink(permalink)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {permalink}")

    file_path = Path(f"{config.home}/{entity.file_path}")
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}",
        )
    return FileResponse(path=file_path)
