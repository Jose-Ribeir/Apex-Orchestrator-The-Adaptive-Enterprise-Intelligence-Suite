"""In-memory RAG provider: local embeddings (sentence-transformers) or keyword fallback. No Vertex/GCP."""

from __future__ import annotations

import math
import re
from typing import Any

from app.providers.rag.base import RAGRetriever

# In-memory store: agent_key -> list of {id, content, vector (optional)}
_store: dict[str, list[dict[str, Any]]] = {}
_retriever_cache: dict[str, MemoryRAGRetriever] = {}


def _safe_agent(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")) or "default"


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Use local sentence-transformers if available, else return empty (keyword fallback)."""
    try:
        from app.services.embedding import init_embedding_model

        model = init_embedding_model()
        out = model.encode(texts, show_progress_bar=False)
        # encode() returns ndarray (n, dim) or (dim,) for single text
        if getattr(out, "ndim", 0) == 1:
            return [out.tolist()]
        return out.tolist()
    except Exception:
        return []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _keyword_score(query: str, doc_content: str) -> float:
    """Simple overlap score when embeddings unavailable."""
    q_words = set(re.findall(r"\w+", query.lower()))
    d_words = set(re.findall(r"\w+", doc_content.lower()))
    if not q_words:
        return 0.0
    return len(q_words & d_words) / len(q_words)


class MemoryRAGRetriever:
    """In-memory retriever for one agent: vector search if embeddings available, else keyword."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self._key = _safe_agent(agent_name)
        if self._key not in _store:
            _store[self._key] = []

    def add_or_update_documents(self, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        texts = [d.get("content") or "" for d in docs]
        vectors = _embed_texts(texts)
        existing = {x["id"]: x for x in _store.get(self._key, [])}
        for i, doc in enumerate(docs):
            doc_id = doc.get("id") or f"doc_{i}"
            vec = vectors[i] if i < len(vectors) and vectors[i] else None
            existing[doc_id] = {
                "id": doc_id,
                "content": doc.get("content") or "",
                "metadata": doc.get("metadata") or {},
                "vector": vec,
            }
        _store[self._key] = list(existing.values())

    def delete_document(self, doc_id: str) -> bool:
        before = len(_store[self._key])
        _store[self._key] = [x for x in _store[self._key] if x["id"] != doc_id]
        return len(_store[self._key]) < before

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        items = _store.get(self._key, [])
        if not items:
            return []
        query_vec = None
        if items and items[0].get("vector"):
            qvecs = _embed_texts([query])
            query_vec = qvecs[0] if qvecs else None
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in items:
            if query_vec and item.get("vector"):
                sim = _cosine_similarity(query_vec, item["vector"])
            else:
                sim = _keyword_score(query, item.get("content") or "")
            scored.append((sim, {"contents": item.get("content") or "", "score": sim}))
        scored.sort(key=lambda x: -x[0])
        return [s[1] for s in scored[:top_k]]

    def count_documents(self) -> int:
        return len(_store.get(self._key, []))


class MemoryRAGProvider:
    """In-memory RAG provider: no Vertex, no GCP. Uses local embeddings or keyword search."""

    def get_or_create_retriever(self, agent_name: str) -> RAGRetriever:
        key = _safe_agent(agent_name)
        if key not in _retriever_cache:
            _retriever_cache[key] = MemoryRAGRetriever(agent_name)
        return _retriever_cache[key]

    def list_agent_names(self) -> list[str]:
        return sorted(_store.keys())

    def list_agents_with_doc_counts(self) -> list[tuple[str, int]]:
        return sorted((k, len(v)) for k, v in _store.items())

    def retriever_cache_keys(self) -> list[str]:
        return list(_retriever_cache.keys())
