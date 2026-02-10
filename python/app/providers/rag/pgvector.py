"""
pgvector RAG provider: PostgreSQL + pgvector extension for shared, persistent vector search.

Uses DATABASE_URL; requires the pgvector extension and rag_embeddings table (migration 006).
Embeddings use the same local model as the memory provider (BAAI/bge-base-en-v1.5);
install sentence-transformers for embedding support (see requirements or docs).
Senior-level: connection-scoped type registration, parameterized queries, explicit resource handling.

Disk usage: PostgreSQL reclaims space via autovacuum (dead rows from UPDATE/DELETE). No app-level
compaction. If the HNSW index grows large after heavy updates, run periodically:
  REINDEX INDEX CONCURRENTLY ix_rag_embeddings_embedding_cosine;
or VACUUM ANALYZE rag_embeddings; (e.g. from cron or a maintenance job).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.db import session_scope
from app.providers.rag.base import RAGRetriever

logger = logging.getLogger(__name__)

_retriever_cache: dict[str, PgVectorRAGRetriever] = {}


def _safe_agent(s: str) -> str:
    """Normalize agent identifier for use as a table key (alphanumeric, hyphen, underscore)."""
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
        logger.warning("pgvector RAG: embedding failed, %s", e)
        return []


def _get_table() -> str:
    """Table name from config; quoted for safe identifier (no injection from env)."""
    raw = (get_settings().rag_pgvector_table or "rag_embeddings").strip()
    if not raw.replace("_", "").isalnum():
        return "rag_embeddings"
    return raw


def _to_vector(lst: list[float]) -> Any:
    """Convert list of floats to pgvector.Vector so psycopg2 binds as vector type, not numeric[]."""
    from pgvector import Vector  # type: ignore[import-untyped]

    return Vector(lst)


class PgVectorRAGRetriever:
    """
    Per-agent RAG retriever backed by PostgreSQL pgvector.

    All operations use the shared rag_embeddings table scoped by agent_key.
    Cosine similarity is used for search (pgvector <=> operator; score returned as 1 - distance).
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
                "pgvector: embedding count %s != doc count %s; skipping upsert",
                len(vectors),
                len(docs),
            )
            return
        table = _get_table()
        dim = get_settings().rag_embedding_dim
        inserted = 0

        with session_scope() as session:
            _register_pgvector(session)
            for i, doc in enumerate(docs):
                doc_id = (doc.get("id") or "").strip() or f"doc_{i}"
                content = (doc.get("content") or "").strip()
                meta = doc.get("metadata")
                if not isinstance(meta, dict):
                    meta = {}
                vec = vectors[i]
                if len(vec) != dim:
                    logger.warning(
                        "pgvector: embedding dim %s != configured %s for doc %s",
                        len(vec),
                        dim,
                        doc_id,
                    )
                    continue
                session.execute(
                    text(f"""
                        INSERT INTO {table} (agent_key, doc_id, content, embedding, metadata)
                        VALUES (:agent_key, :doc_id, :content, :embedding, CAST(:metadata AS jsonb))
                        ON CONFLICT (agent_key, doc_id)
                        DO UPDATE SET content = EXCLUDED.content,
                                      embedding = EXCLUDED.embedding,
                                      metadata = EXCLUDED.metadata
                    """),
                    {
                        "agent_key": self._agent_key,
                        "doc_id": doc_id,
                        "content": content,
                        "embedding": _to_vector(vec),
                        "metadata": json.dumps(meta),
                    },
                )
                inserted += 1
        if inserted:
            logger.info(
                "pgvector: add_or_update_documents agent_key=%s documents_count=%s",
                self._agent_key,
                inserted,
            )

    def delete_document(self, doc_id: str) -> bool:
        if not doc_id:
            return False
        table = _get_table()
        with session_scope() as session:
            result = session.execute(
                text(f"DELETE FROM {table} WHERE agent_key = :agent_key AND doc_id = :doc_id"),
                {"agent_key": self._agent_key, "doc_id": doc_id.strip()},
            )
            deleted = result.rowcount > 0
        if deleted:
            logger.info("pgvector: delete_document agent_key=%s doc_id=%s", self._agent_key, doc_id.strip())
        return deleted

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        qvecs = _embed_texts([query])
        if not qvecs:
            return []
        table = _get_table()
        with session_scope() as session:
            _register_pgvector(session)
            rows = session.execute(
                text(f"""
                    SELECT content,
                           1 - (embedding <=> :embedding) AS score
                    FROM {table}
                    WHERE agent_key = :agent_key
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                """),
                {
                    "agent_key": self._agent_key,
                    "embedding": _to_vector(qvecs[0]),
                    "limit": max(1, min(top_k, 100)),
                },
            ).fetchall()
        return [{"contents": (r[0] or "").strip(), "score": float(r[1] or 0.0)} for r in rows]

    def count_documents(self) -> int:
        table = _get_table()
        with session_scope() as session:
            row = session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE agent_key = :agent_key"),
                {"agent_key": self._agent_key},
            ).fetchone()
        return int(row[0]) if row else 0

    def get_all_content_for_context(self, max_tokens: int) -> tuple[str, int] | None:
        table = _get_table()
        with session_scope() as session:
            rows = session.execute(
                text(f"SELECT content FROM {table} WHERE agent_key = :agent_key"),
                {"agent_key": self._agent_key},
            ).fetchall()
        if not rows:
            return ("", 0)
        parts = [(r[0] or "").strip() for r in rows if (r[0] or "").strip()]
        concatenated = "\n\n".join(parts)
        estimated_tokens = len(concatenated) // 4
        if estimated_tokens > max_tokens:
            return None
        return (concatenated, estimated_tokens)


def _register_pgvector(session: Any) -> None:
    """Register pgvector type on the session's connection so vector params work."""
    try:
        from pgvector.psycopg2 import register_vector  # type: ignore[import-untyped]
    except ImportError:
        try:
            from pgvector.psycopg import register_vector  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("pgvector.psycopg2/psycopg not found; vector params may fail")
            return
    # SQLAlchemy 2: session.connection().connection is the pool proxy; use dbapi_connection for psycopg2
    conn = session.connection()
    proxy = getattr(conn, "connection", None)
    raw = getattr(proxy, "dbapi_connection", getattr(proxy, "driver_connection", proxy))
    if raw is not None:
        register_vector(raw)


class PgVectorRAGProvider:
    """RAG provider backed by PostgreSQL pgvector. Shared across API and worker processes."""

    def get_or_create_retriever(self, agent_name: str) -> RAGRetriever:
        key = _safe_agent(agent_name)
        if key not in _retriever_cache:
            _retriever_cache[key] = PgVectorRAGRetriever(agent_name)
        return _retriever_cache[key]

    def list_agent_names(self) -> list[str]:
        table = _get_table()
        with session_scope() as session:
            rows = session.execute(text(f"SELECT DISTINCT agent_key FROM {table} ORDER BY agent_key")).fetchall()
        return [r[0] for r in rows if r[0]]

    def list_agents_with_doc_counts(self) -> list[tuple[str, int]]:
        table = _get_table()
        with session_scope() as session:
            rows = session.execute(
                text(f"SELECT agent_key, COUNT(*) FROM {table} GROUP BY agent_key ORDER BY agent_key")
            ).fetchall()
        return [(r[0], int(r[1])) for r in rows if r[0]]

    def retriever_cache_keys(self) -> list[str]:
        return list(_retriever_cache.keys())
