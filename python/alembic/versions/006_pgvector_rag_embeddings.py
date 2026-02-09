"""Add pgvector extension and rag_embeddings table for RAG_PROVIDER=pgvector.

Revision ID: 006_pgvector
Revises: 005_enrich
Create Date: 2026-02-09

Table stores per-agent document chunks with embeddings for cosine similarity search.

Install pgvector in PostgreSQL before running this migration:

  Docker:  Use image pgvector/pgvector:pg16 (or pg15) instead of postgres:16.
  Ubuntu:  sudo apt install postgresql-16-pgvector  (match your PG version).
  macOS:   brew install pgvector
  From source: https://github.com/pgvector/pgvector#installation
"""

from collections.abc import Sequence

import sqlalchemy
from alembic import op

revision: str = "006_pgvector"
down_revision: str | None = "005_enrich"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except sqlalchemy.exc.NotSupportedError as e:
        raise RuntimeError(
            "pgvector extension is not installed on this PostgreSQL server. "
            "Install it first: Docker use image pgvector/pgvector:pg16; "
            "Ubuntu: apt install postgresql-16-pgvector; macOS: brew install pgvector. "
            "See migration 006_pgvector_rag_embeddings.py docstring."
        ) from e

    op.execute("""
        CREATE TABLE IF NOT EXISTS rag_embeddings (
            id BIGSERIAL PRIMARY KEY,
            agent_key TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (agent_key, doc_id)
        )
    """)
    op.create_index(
        "ix_rag_embeddings_agent_key",
        "rag_embeddings",
        ["agent_key"],
        unique=False,
    )
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_rag_embeddings_embedding_cosine
        ON rag_embeddings
        USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.drop_index("ix_rag_embeddings_embedding_cosine", table_name="rag_embeddings")
    op.drop_index("ix_rag_embeddings_agent_key", table_name="rag_embeddings")
    op.drop_table("rag_embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
