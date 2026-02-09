"""Add source_type and source_url to agent_documents (knowledge base: file, text, url).

Revision ID: 010_agent_documents_source
Revises: 009_connection_types
Create Date: 2026-02-09

"""

from collections.abc import Sequence

from alembic import op

revision: str = "010_agent_documents_source"
down_revision: str | None = "009_connection_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent_documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(32)")
    op.execute("ALTER TABLE agent_documents ADD COLUMN IF NOT EXISTS source_url TEXT")
    # Backfill: file when we have storage or filename, else text for legacy
    op.execute("""
        UPDATE agent_documents
        SET source_type = 'file'
        WHERE source_type IS NULL AND (storage_path IS NOT NULL OR source_filename IS NOT NULL)
    """)
    op.execute("""
        UPDATE agent_documents
        SET source_type = 'text'
        WHERE source_type IS NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE agent_documents DROP COLUMN IF EXISTS source_url")
    op.execute("ALTER TABLE agent_documents DROP COLUMN IF EXISTS source_type")
