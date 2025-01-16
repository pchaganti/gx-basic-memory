"""Routes for memory:// URI operations."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter

from basic_memory.schemas.memory import MemoryUrl, GraphContext
from basic_memory.deps import ContextServiceDep

router = APIRouter(prefix="/memory")


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
    # Parse URI
    memory_url = MemoryUrl.parse(f"memory://{uri}")

    # Parse timeframe
    since = parse_timeframe(timeframe)

    # Build context
    context = await context_service.build_context(str(memory_url), depth=depth, since=since)

    # Transform to GraphContext
    return GraphContext.model_validate(context)


@router.get("/related/{permalink}", response_model=GraphContext)
async def get_related_context(
    context_service: ContextServiceDep,
    permalink: str,
    relation_types: Optional[List[str]] = None,
    depth: int = 1,
) -> GraphContext:
    """Get context for related entities."""
    # Build special related URI with params
    memory_url = MemoryUrl.parse(f"memory://related/{permalink}")
    memory_url.params["type"] = "related"
    memory_url.params["target"] = permalink
    if relation_types:
        memory_url.params["relation_types"] = relation_types

    # Build context
    context = await context_service.build_context(str(memory_url), depth=depth)

    # Transform to GraphContext
    return GraphContext.model_validate(context)
