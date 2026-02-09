"""RAG providers: vertex (Vertex AI), memory (in-memory), pgvector (PostgreSQL), lancedb (embedded)."""

from app.config import get_settings
from app.providers.rag.base import RAGProvider, RAGRetriever
from app.providers.rag.lancedb import LanceDBRAGProvider
from app.providers.rag.memory import MemoryRAGProvider
from app.providers.rag.pgvector import PgVectorRAGProvider
from app.providers.rag.vertex import VertexRAGProvider

_PROVIDER: RAGProvider | None = None


def get_rag_provider() -> RAGProvider:
    """Return the configured RAG provider (vertex | memory | pgvector | lancedb). Cached per process."""
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    settings = get_settings()
    name = (settings.rag_provider or "vertex").strip().lower()
    if name == "memory":
        _PROVIDER = MemoryRAGProvider()
    elif name == "pgvector":
        _PROVIDER = PgVectorRAGProvider()
    elif name == "lancedb":
        _PROVIDER = LanceDBRAGProvider()
    else:
        _PROVIDER = VertexRAGProvider()
    return _PROVIDER


__all__ = [
    "RAGProvider",
    "RAGRetriever",
    "get_rag_provider",
    "VertexRAGProvider",
    "MemoryRAGProvider",
    "PgVectorRAGProvider",
    "LanceDBRAGProvider",
]
