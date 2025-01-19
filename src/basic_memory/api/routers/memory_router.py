"""Routes for memory:// URI operations."""

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter
from loguru import logger

from basic_memory.config import config
from basic_memory.deps import ContextServiceDep
from basic_memory.schemas.memory import MemoryUrl, GraphContext
from basic_memory.schemas.search import SearchResult, RelatedResult

router = APIRouter(prefix="/memory", tags=["memory"])


def parse_timeframe(timeframe: str) -> Optional[datetime]:
    """Convert timeframe string to datetime.

    Formats:
    - 7d: 7 days ago
    - 30d: 30 days ago
    - None: no time limit
    """
    if not timeframe:
        return None

    if not timeframe.endswith("d"):
        raise ValueError("Timeframe must be in days (e.g., '7d')")

    days = int(timeframe[:-1])
    return datetime.utcnow() - timedelta(days=days)


@router.get("/{uri:path}", response_model=GraphContext)
async def get_memory_context(
    context_service: ContextServiceDep,
    uri: str,
    depth: int = 1,
    timeframe: str = "7d",
    max_results: int = 10,
) -> GraphContext:
    """Get rich context from memory:// URI."""
    # add the project name from the config to the url as the "host
    # Parse URI
    logger.debug(f"Getting context for URI: `{uri}` depth: `{depth}` timeframe: `{timeframe}` max_results: `{max_results}`")
    memory_url = MemoryUrl(f"memory://{config.project}/{uri}")

    # Parse timeframe
    since = parse_timeframe(timeframe)

    # Build context
    context = await context_service.build_context(
        memory_url, depth=depth, since=since, max_results=max_results
    )

    primary_results = [SearchResult(**asdict(r)) for r in context["primary_results"]]
    related_results = [RelatedResult(**asdict(r)) for r in context["related_results"]]
    metadata = context["metadata"]
    # Transform to GraphContext
    return GraphContext(
        primary_results=primary_results, related_results=related_results, metadata=metadata
    )
