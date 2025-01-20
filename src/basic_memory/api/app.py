"""FastAPI application for basic-memory knowledge graph API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from basic_memory import db
from .routers import knowledge, discovery, search, memory, resource


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    logger.info("Starting Basic Memory API")
    yield
    logger.info("Shutting down Basic Memory API")
    await db.shutdown_db()


# Initialize FastAPI app
app = FastAPI(
    title="Basic Memory API",
    description="Knowledge graph API for basic-memory",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(knowledge.router)
app.include_router(discovery.router)
app.include_router(search.router)
app.include_router(memory.router)
app.include_router(resource.router)