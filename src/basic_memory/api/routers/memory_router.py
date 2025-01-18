"""Routes for memory:// URI operations."""
from dataclasses import asdict
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter

from basic_memory.config import config
from basic_memory.schemas.memory import MemoryUrl, GraphContext
from basic_memory.deps import ContextServiceDep
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
) -> GraphContext:
    """Get rich context from memory:// URI."""
    # add the project name from the config to the url as the "host
    # Parse URI
    memory_url = MemoryUrl(f"memory://{config.project}/{uri}")

    # Parse timeframe
    since = parse_timeframe(timeframe)

    # Build context
    context = await context_service.build_context(memory_url, depth=depth, since=since)

    primary_entities = [SearchResult(**asdict(r)) for r in context["primary_entities"]]
    related_entities = [RelatedResult(**asdict(r)) for r in context["related_entities"]]
    metadata = context["metadata"]
    # Transform to GraphContext
    return GraphContext(primary_entities=primary_entities, related_entities=related_entities, metadata=metadata)

