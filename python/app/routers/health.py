"""Health check and model listing."""

import asyncio

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.db import check_connection
from app.schemas.responses import HealthResponse
from app.services.gemini_router import list_models as gemini_list_models
from app.services.rag import retriever_cache

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns status, agents with RAG, GeminiMesh flag, RAG/LLM providers, and DB status.",
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
        embedding_model=settings.rag_provider or "vertex",
        database_configured=settings.database_configured,
        database_connected=database_connected,
    )


@router.get(
    "/models",
    summary="List Gemini models",
    description="List available Gemini models and their supported methods (e.g. generateContent). Use when resolving 404 NOT_FOUND for a model name.",
)
async def models_list():
    """Return available models from the Gemini API (only when LLM_PROVIDER=gemini)."""
    settings = get_settings()
    if settings.llm_provider != "gemini":
        raise HTTPException(
            status_code=400,
            detail=f"List models is only available when LLM_PROVIDER=gemini (current: {settings.llm_provider})",
        )
    try:
        return await asyncio.to_thread(gemini_list_models)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
