"""Business logic: embeddings, RAG, Gemini routing and generation."""

from app.services.embedding import get_embedding_model, init_embedding_model
from app.services.gemini_router import (
    build_optimized_prompt,
    optimize_agent_prompt,
    run_cheap_router,
    run_generator_stream,
)
from app.services.geminimesh import update_agent_in_geminimesh
from app.services.rag import get_or_create_retriever

__all__ = [
    "get_embedding_model",
    "init_embedding_model",
    "get_or_create_retriever",
    "run_cheap_router",
    "run_generator_stream",
    "optimize_agent_prompt",
    "build_optimized_prompt",
    "update_agent_in_geminimesh",
]
