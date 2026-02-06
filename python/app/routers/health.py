"""Health check endpoint."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.responses import HealthResponse
from app.services.embedding import get_embedding_model
from app.services.rag import retriever_cache

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns status, list of agents with loaded RAG, GeminiMesh config flag, and embedding model load state.",
    operation_id="getHealth",
)
async def health() -> HealthResponse:
    settings = get_settings()
    model = get_embedding_model()
    return HealthResponse(
        status="healthy",
        agents=list(retriever_cache.keys()),
        geminimesh_configured=settings.geminimesh_configured,
        embedding_model="loaded" if model else "not_loaded",
    )
