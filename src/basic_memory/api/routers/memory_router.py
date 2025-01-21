"""Routes for memory:// URI operations."""

from datetime import datetime, timedelta
from typing import Optional, List, Annotated

from dateparser import parse
from fastapi import APIRouter, Query
from loguru import logger

from basic_memory.config import config
from basic_memory.deps import ContextServiceDep, EntityRepositoryDep
from basic_memory.repository import EntityRepository
from basic_memory.repository.search_repository import SearchIndexRow
from basic_memory.schemas.base import TimeFrame
from basic_memory.schemas.memory import (
    MemoryUrl,
    GraphContext,
    RelationSummary,
    EntitySummary,
    ObservationSummary,
    MemoryMetadata,
)
from basic_memory.schemas.search import SearchItemType
from basic_memory.services.context_service import ContextResultRow

router = APIRouter(prefix="/memory", tags=["memory"])



async def to_graph_context(context, entity_repository: EntityRepository):
    # return results
    async def to_summary(item: SearchIndexRow | ContextResultRow):
        match item.type:
            case SearchItemType.ENTITY:
                return EntitySummary(
                    title=item.title,
                    permalink=item.permalink,
                    file_path=item.file_path,
                    created_at=item.created_at,
                )
            case SearchItemType.OBSERVATION:
                return ObservationSummary(
                    category=item.category, content=item.content, permalink=item.permalink
                )
            case SearchItemType.RELATION:
                from_entity = await entity_repository.find_by_id(item.from_id)
                to_entity = await entity_repository.find_by_id(item.to_id)

                return RelationSummary(
                    permalink=item.permalink,
                    type=item.type,
                    from_id=from_entity.permalink,
                    to_id=to_entity.permalink,
                    created_at=item.created_at,
                )

    primary_results = [await to_summary(r) for r in context["primary_results"]]
    related_results = [await to_summary(r) for r in context["related_results"]]
    metadata = MemoryMetadata.model_validate(context["metadata"])
    # Transform to GraphContext
    return GraphContext(
        primary_results=primary_results, related_results=related_results, metadata=metadata
    )



@router.get("/recent", response_model=GraphContext)
async def recent(
    context_service: ContextServiceDep,
    entity_repository: EntityRepositoryDep,
    type: Annotated[list[SearchItemType] | None, Query()] = None,
    depth: int = 1,
    timeframe: TimeFrame = "7d",
    max_results: int = 10,
) -> GraphContext:
    # return all types by default
    types = (
        [SearchItemType.ENTITY, SearchItemType.RELATION, SearchItemType.OBSERVATION]
        if not type
        else type
    )

    logger.debug(
        f"Getting recent context: `{types}` depth: `{depth}` timeframe: `{timeframe}` max_results: `{max_results}`"
    )
    # Parse timeframe
    since = parse(timeframe)

    # Build context
    context = await context_service.build_context(
        types=types, depth=depth, since=since, max_results=max_results
    )
    return await to_graph_context(context, entity_repository=entity_repository)


# get_memory_context needs to be declared last so other paths can match 

@router.get("/{uri:path}", response_model=GraphContext)
async def get_memory_context(
    context_service: ContextServiceDep,
    entity_repository: EntityRepositoryDep,
    uri: str,
    depth: int = 1,
    timeframe: TimeFrame = "7d",
    max_results: int = 10,
) -> GraphContext:
    """Get rich context from memory:// URI."""
    # add the project name from the config to the url as the "host
    # Parse URI
    logger.debug(
        f"Getting context for URI: `{uri}` depth: `{depth}` timeframe: `{timeframe}` max_results: `{max_results}`"
    )
    memory_url = MemoryUrl(f"memory://{uri}")

    # Parse timeframe
    since = parse(timeframe)

    # Build context
    context = await context_service.build_context(
        memory_url, depth=depth, since=since, max_results=max_results
    )
    return await to_graph_context(context, entity_repository=entity_repository)



