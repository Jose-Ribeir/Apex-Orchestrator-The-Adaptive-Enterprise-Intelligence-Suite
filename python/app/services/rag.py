"""
RAG: provider-agnostic facade. Dispatches to Vertex or in-memory based on RAG_PROVIDER.
Google integration remains in rag_vertex; alternative in providers.rag.memory.
"""

from app.providers.rag import get_rag_provider


def get_or_create_retriever(agent_name: str):
    """Return RAG retriever for the agent (Vertex or memory per RAG_PROVIDER)."""
    return get_rag_provider().get_or_create_retriever(agent_name)


def list_agent_names_from_disk() -> list[str]:
    """List agent names that have indexed documents (provider-specific source)."""
    return get_rag_provider().list_agent_names()


def list_agents_with_doc_counts() -> list[tuple[str, int]]:
    """List (agent_name, doc_count) sorted by name."""
    return get_rag_provider().list_agents_with_doc_counts()


def retriever_cache_keys() -> list[str]:
    """Cache keys for health/debug (provider-specific)."""
    return get_rag_provider().retriever_cache_keys()


# Backward compat: health used list(retriever_cache.keys())
class _RetrieverCacheKeys:
    def keys(self):
        return retriever_cache_keys()


retriever_cache = _RetrieverCacheKeys()


__all__ = [
    "get_or_create_retriever",
    "list_agent_names_from_disk",
    "list_agents_with_doc_counts",
    "retriever_cache",
    "retriever_cache_keys",
]
