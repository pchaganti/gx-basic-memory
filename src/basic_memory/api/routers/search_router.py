"""Router for search operations."""

from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks

from basic_memory.schemas.search import SearchQuery, SearchResult, SearchResponse
from basic_memory.deps import SearchServiceDep

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search(
    query: SearchQuery,
    search_service: SearchServiceDep,
    page: int = 1,
    page_size: int = 10,
):
    """Search across all knowledge and documents."""
    limit = page_size
    offset = (page - 1) * page_size
    results = await search_service.search(query, limit=limit, offset=offset)
    search_results = [SearchResult.model_validate(asdict(r)) for r in results]
    return SearchResponse(
        results=search_results,
        current_page=page,
        page_size=page_size,
    )


@router.post("/reindex")
async def reindex(background_tasks: BackgroundTasks, search_service: SearchServiceDep):
    """Recreate and populate the search index."""
    await search_service.reindex_all(background_tasks=background_tasks)
    return {"status": "ok", "message": "Reindex initiated"}
