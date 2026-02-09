"""
Provider abstractions for RAG, LLM, and storage.
Allows multiple backends (Google/Vertex, OpenAI, in-memory, local) without removing existing integrations.
"""

from app.providers.llm import get_llm_provider
from app.providers.rag import get_rag_provider
from app.providers.storage import get_storage_provider

__all__ = [
    "get_rag_provider",
    "get_llm_provider",
    "get_storage_provider",
]
