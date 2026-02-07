"""
RAG: Vertex AI only (Embeddings + Vector Search).
Re-exports from rag_vertex. No LanceDB or local embeddings.
"""

from app.services.rag_vertex import (
    get_or_create_retriever,
    list_agent_names_from_disk,
    list_agents_with_doc_counts,
    retriever_cache,
)

__all__ = [
    "get_or_create_retriever",
    "list_agent_names_from_disk",
    "list_agents_with_doc_counts",
    "retriever_cache",
]
