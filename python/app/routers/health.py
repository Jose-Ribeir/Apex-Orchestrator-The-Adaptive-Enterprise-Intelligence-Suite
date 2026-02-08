"""Health check endpoint."""

import asyncio

from fastapi import APIRouter

from app.config import get_settings
from app.db import check_connection
from app.schemas.responses import HealthResponse
from app.services.rag import retriever_cache

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns status, agents with RAG, GeminiMesh flag, embedding backend, and DB status.",
    operation_id="getHealth",
)
async def health() -> HealthResponse:
    settings = get_settings()
    database_connected = False
    if settings.database_configured:
        database_connected = await asyncio.to_thread(check_connection)
    return HealthResponse(
        status="healthy",
        agents=list(retriever_cache.keys()),
        geminimesh_configured=settings.geminimesh_configured,
        embedding_model="vertex",
        database_configured=settings.database_configured,
        database_connected=database_connected,
    )
