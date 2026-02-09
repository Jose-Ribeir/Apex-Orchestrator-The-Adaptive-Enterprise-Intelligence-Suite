"""Business logic: RAG, LLM (provider-agnostic), GeminiMesh."""

from app.services.gemini_router import build_optimized_prompt  # used internally by Gemini
from app.services.geminimesh import update_agent_in_geminimesh
from app.services.llm import (
    optimize_agent_prompt,
    run_cheap_router,
    run_generator_stream,
)
from app.services.rag import get_or_create_retriever

__all__ = [
    "get_or_create_retriever",
    "run_cheap_router",
    "run_generator_stream",
    "optimize_agent_prompt",
    "build_optimized_prompt",
    "update_agent_in_geminimesh",
]
