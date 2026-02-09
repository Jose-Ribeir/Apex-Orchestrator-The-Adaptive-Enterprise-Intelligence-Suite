"""RAG provider protocol: per-agent retriever and provider factory."""

from typing import Any, Protocol


class RAGRetriever(Protocol):
    """Per-agent RAG: add/update docs, delete, search, count. Implementations are provider-specific."""

    def add_or_update_documents(self, docs: list[dict[str, Any]]) -> None:
        """Upsert documents (each has 'id', 'content', optional 'metadata')."""
        ...

    def delete_document(self, doc_id: str) -> bool:
        """Remove document by id. Returns True if removed."""
        ...

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return list of dicts with 'contents' and 'score'."""
        ...

    def count_documents(self) -> int:
        """Total document count for this agent."""
        ...


class RAGProvider(Protocol):
    """Factory + listing. One implementation per backend (vertex, memory, etc.)."""

    def get_or_create_retriever(self, agent_name: str) -> RAGRetriever:
        """Return a RAGRetriever for the given agent (cached per provider)."""
        ...

    def list_agent_names(self) -> list[str]:
        """List agent names that have indexed documents (provider-specific source)."""
        ...

    def list_agents_with_doc_counts(self) -> list[tuple[str, int]]:
        """List (agent_name, doc_count) sorted by name."""
        ...

    def retriever_cache_keys(self) -> list[str]:
        """Keys of currently cached retrievers (for health/debug)."""
        ...
