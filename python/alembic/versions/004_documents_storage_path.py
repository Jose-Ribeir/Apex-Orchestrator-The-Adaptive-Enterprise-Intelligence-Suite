"""Add storage_path and remove content_preview from agent_documents.

Revision ID: 004_storage_path
Revises: 003_rag_ids
Create Date: 2026-02-07

DB stores only file metadata and GCS path; no content/chunks (RAG responsibility).
Signed URLs are generated at read time from storage_path.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "004_storage_path"
down_revision: str | None = "003_rag_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agent_documents' AND column_name = 'storage_path'
            ) THEN
                ALTER TABLE agent_documents ADD COLUMN storage_path TEXT;
            END IF;
        END $$
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agent_documents' AND column_name = 'content_preview'
            ) THEN
                ALTER TABLE agent_documents DROP COLUMN content_preview;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agent_documents' AND column_name = 'storage_path'
            ) THEN
                ALTER TABLE agent_documents DROP COLUMN storage_path;
            END IF;
        END $$
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agent_documents' AND column_name = 'content_preview'
            ) THEN
                ALTER TABLE agent_documents ADD COLUMN content_preview TEXT;
            END IF;
        END $$
    """)
