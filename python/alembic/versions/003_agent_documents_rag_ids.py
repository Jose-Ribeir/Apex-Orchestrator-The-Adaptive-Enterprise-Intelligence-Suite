"""Add agent_documents.rag_document_ids for one row per file.

Revision ID: 003_rag_ids
Revises: 002_agents_metadata
Create Date: 2026-02-07

Stores all RAG chunk IDs per file so we show one row per uploaded file
and delete all chunks when the user removes a document.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_rag_ids"
down_revision: str | None = "002_agents_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agent_documents' AND column_name = 'rag_document_ids'
            ) THEN
                ALTER TABLE agent_documents ADD COLUMN rag_document_ids JSONB DEFAULT '[]';
                UPDATE agent_documents
                SET rag_document_ids = jsonb_build_array(document_id)
                WHERE rag_document_ids = '[]' OR rag_document_ids IS NULL;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agent_documents' AND column_name = 'rag_document_ids'
            ) THEN
                ALTER TABLE agent_documents DROP COLUMN rag_document_ids;
            END IF;
        END $$
    """)
