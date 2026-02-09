"""Vertex AI RAG provider: delegates to existing rag_vertex (no code duplication)."""

from app.providers.rag.base import RAGRetriever


class VertexRAGProvider:
    """RAG provider using Vertex AI Vector Search + GCS registry."""

    def get_or_create_retriever(self, agent_name: str) -> RAGRetriever:
        from app.services import rag_vertex

        return rag_vertex.get_or_create_retriever(agent_name)

    def list_agent_names(self) -> list[str]:
        from app.services import rag_vertex

        return rag_vertex.list_agent_names_from_disk()

    def list_agents_with_doc_counts(self) -> list[tuple[str, int]]:
        from app.services import rag_vertex

        return rag_vertex.list_agents_with_doc_counts()

    def retriever_cache_keys(self) -> list[str]:
        from app.services import rag_vertex

        return list(rag_vertex.retriever_cache.keys())
