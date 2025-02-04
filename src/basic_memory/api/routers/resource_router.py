"""Routes for getting entity content."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from basic_memory.deps import ProjectConfigDep, LinkResolverDep

router = APIRouter(prefix="/resource", tags=["resources"])


@router.get("/{identifier:path}")
async def get_resource_content(
    config: ProjectConfigDep,
    link_resolver: LinkResolverDep,
    identifier: str,
) -> FileResponse:
    """Get resource content by identifier: name or permalink."""
    logger.debug(f"Getting content for permalink: {identifier}")

    # Find entity by permalink
    entity = await link_resolver.resolve_link(identifier)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {identifier}")

    file_path = Path(f"{config.home}/{entity.file_path}")
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}",
        )
    return FileResponse(path=file_path)
