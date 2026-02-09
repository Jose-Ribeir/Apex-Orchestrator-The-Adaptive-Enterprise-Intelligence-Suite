"""
LanceDB RAG provider: embedded, file-based vector DB for per-agent RAG.

Uses RAG_LANCEDB_PATH; no PostgreSQL or Vertex required. Embeddings use the same
local model as memory/pgvector (BAAI/bge-base-en-v1.5). Install sentence-transformers
for embedding support.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pyarrow as pa

from app.config import get_settings
from app.providers.rag.base import RAGRetriever

logger = logging.getLogger(__name__)

_retriever_cache: dict[str, LanceDBRAGRetriever] = {}
_db: Any = None
_table_name = "rag_docs"


def _safe_agent(s: str) -> str:
    """Normalize agent identifier (alphanumeric, hyphen, underscore)."""
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")) or "default"


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts using the app's embedding model. Returns list of vectors; empty on failure."""
    if not texts:
        return []
    try:
        from app.services.embedding import init_embedding_model

        model = init_embedding_model()
        out = model.encode(texts, show_progress_bar=False)
        if getattr(out, "ndim", 0) == 1:
            return [out.tolist()]
        return out.tolist()
    except Exception as e:
        logger.warning("lancedb RAG: embedding failed, %s", e)
        return []


def _get_db():
    """Connect to LanceDB at configured path. Creates directory if needed."""
    global _db
    if _db is not None:
        return _db
    import lancedb

    path = (get_settings().rag_lancedb_path or "data/lancedb").strip()
    path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    _db = lancedb.connect(path)
    return _db


def _rag_schema(dim: int) -> pa.Schema:
    """Arrow schema for RAG table: row_id (key), agent_key, doc_id, content, vector, metadata."""
    return pa.schema(
        [
            ("row_id", pa.string()),
            ("agent_key", pa.string()),
            ("doc_id", pa.string()),
            ("content", pa.string()),
            ("vector", pa.list_(pa.float32(), dim)),
            ("metadata", pa.string()),
        ]
    )


def _get_table():
    """Return or create the shared RAG table."""
    db = _get_db()
    dim = get_settings().rag_embedding_dim
    if _table_name in db.table_names():
        return db.open_table(_table_name)
    return db.create_table(_table_name, schema=_rag_schema(dim), mode="overwrite")


class LanceDBRAGRetriever:
    """
    Per-agent RAG retriever backed by LanceDB.

    Uses a single shared table scoped by agent_key. Cosine similarity for search.
    """

    __slots__ = ("_agent_key", "_agent_name")

    def __init__(self, agent_name: str) -> None:
        self._agent_name = agent_name
        self._agent_key = _safe_agent(agent_name)

    def add_or_update_documents(self, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        texts = [d.get("content") or "" for d in docs]
        vectors = _embed_texts(texts)
        if len(vectors) != len(docs):
            logger.warning(
                "lancedb: embedding count %s != doc count %s; skipping upsert",
                len(vectors),
                len(docs),
            )
            return
        dim = get_settings().rag_embedding_dim
        table = _get_table()

        rows = []
        for i, doc in enumerate(docs):
            doc_id = (doc.get("id") or "").strip() or f"doc_{i}"
            content = (doc.get("content") or "").strip()
            meta = doc.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
            vec = vectors[i]
            if len(vec) != dim:
                logger.warning(
                    "lancedb: embedding dim %s != configured %s for doc %s",
                    len(vec),
                    dim,
                    doc_id,
                )
                continue
            row_id = f"{self._agent_key}|{doc_id}"
            rows.append(
                {
                    "row_id": row_id,
                    "agent_key": self._agent_key,
                    "doc_id": doc_id,
                    "content": content,
                    "vector": vec,
                    "metadata": json.dumps(meta),
                }
            )

        if not rows:
            return
        try:
            table.merge_insert("row_id").when_not_matched_insert_all().when_matched_update_all().execute(
                pa.table(
                    {
                        "row_id": pa.array([r["row_id"] for r in rows]),
                        "agent_key": pa.array([r["agent_key"] for r in rows]),
                        "doc_id": pa.array([r["doc_id"] for r in rows]),
                        "content": pa.array([r["content"] for r in rows]),
                        "vector": pa.array([r["vector"] for r in rows], type=pa.list_(pa.float32(), dim)),
                        "metadata": pa.array([r["metadata"] for r in rows]),
                    }
                )
            )
        except Exception as e:
            logger.warning("lancedb merge_insert failed, %s", e)
            # Fallback: delete existing by doc_id then add (no native upsert in older lancedb)
            for r in rows:
                table.delete(f"row_id = '{r['row_id']}'")
            table.add(rows)

    def delete_document(self, doc_id: str) -> bool:
        if not doc_id:
            return False
        # Escape single quotes for SQL predicate
        row_id = f"{self._agent_key}|{doc_id.strip()}".replace("'", "''")
        table = _get_table()
        try:
            table.delete(f"row_id = '{row_id}'")
            return True
        except Exception as e:
            logger.warning("lancedb delete failed, %s", e)
            return False

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        qvecs = _embed_texts([query])
        if not qvecs:
            return []
        table = _get_table()
        limit = max(1, min(top_k, 100))
        try:
            # LanceDB cosine: distance 0 = same direction; convert to similarity score
            safe_key = self._agent_key.replace("'", "''")
            results = (
                table.search(qvecs[0]).where(f"agent_key = '{safe_key}'").distance_type("cosine").limit(limit).to_list()
            )
        except Exception as e:
            logger.warning("lancedb search failed, %s", e)
            return []
        out = []
        for r in results:
            # cosine distance: 0 = identical; 2 = opposite. Score as 1 - (distance/2) in [0,1] or use _distance
            dist = float(getattr(r, "_distance", r.get("_distance", 0.0)))
            score = max(0.0, 1.0 - dist) if dist <= 2.0 else 0.0
            content = (r.get("content") or getattr(r, "content", "") or "").strip()
            out.append({"contents": content, "score": score})
        return out

    def count_documents(self) -> int:
        table = _get_table()
        try:
            import pyarrow.compute as pc

            arrow = table.to_arrow()
            if arrow.num_rows == 0:
                return 0
            mask = pc.equal(arrow["agent_key"], self._agent_key)
            filtered = arrow.filter(mask)
            return filtered.num_rows
        except Exception as e:
            logger.warning("lancedb count failed, %s", e)
            return 0


class LanceDBRAGProvider:
    """RAG provider backed by LanceDB. File-based, shared across API and worker when using same path."""

    def get_or_create_retriever(self, agent_name: str) -> RAGRetriever:
        key = _safe_agent(agent_name)
        if key not in _retriever_cache:
            _retriever_cache[key] = LanceDBRAGRetriever(agent_name)
        return _retriever_cache[key]

    def list_agent_names(self) -> list[str]:
        table = _get_table()
        try:
            arrow = table.to_arrow()
            if arrow.num_rows == 0:
                return []
            agent_col = arrow["agent_key"]
            seen: set[str] = set()
            for i in range(arrow.num_rows):
                seen.add(agent_col[i].as_py())
            return sorted(seen)
        except Exception as e:
            logger.warning("lancedb list_agent_names failed, %s", e)
            return []

    def list_agents_with_doc_counts(self) -> list[tuple[str, int]]:
        table = _get_table()
        try:
            arrow = table.to_arrow()
            if arrow.num_rows == 0:
                return []
            import pyarrow.compute as pc
            from collections import Counter

            agent_col = arrow["agent_key"]
            counts = Counter(agent_col[i].as_py() for i in range(arrow.num_rows))
            return sorted(counts.items())
        except Exception as e:
            logger.warning("lancedb list_agents_with_doc_counts failed, %s", e)
            return []

    def retriever_cache_keys(self) -> list[str]:
        return list(_retriever_cache.keys())
