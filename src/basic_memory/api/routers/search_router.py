"""Router for search operations."""

from fastapi import APIRouter, Depends, BackgroundTasks
from typing import List

from loguru import logger
from basic_memory.services.search_service import SearchService
from basic_memory.schemas.search import SearchQuery, SearchResult
from basic_memory.deps import get_search_service

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=List[SearchResult])
async def search(
    query: SearchQuery,
    search_service: SearchService = Depends(get_search_service)
):
    """Search across all knowledge and documents."""
    return await search_service.search(query)

@router.post("/reindex")
async def reindex(
    background_tasks: BackgroundTasks,
    search_service: SearchService = Depends(get_search_service)
):
    """Recreate and populate the search index."""
    await search_service.reindex_all(background_tasks=background_tasks)
    return {
        "status": "ok",
        "message": "Reindex initiated"
    }