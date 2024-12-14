"""FastAPI application for basic-memory knowledge graph API."""

from fastapi import FastAPI
from loguru import logger

from .routers import knowledge


# Initialize FastAPI app
app = FastAPI(
    title="Basic Memory API",
    description="Knowledge graph API for basic-memory",
    version="0.1.0"
)

# Include routers
app.include_router(knowledge.router)

# Add startup event
@app.on_event("startup")
async def startup_event():
    """Log when the API starts."""
    logger.info("Starting Basic Memory API")
