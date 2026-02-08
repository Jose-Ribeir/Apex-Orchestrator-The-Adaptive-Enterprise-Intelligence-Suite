"""Add agents.metadata column if missing.

Revision ID: 002_agents_metadata
Revises: 001_unified
Create Date: 2026-02-07

Use when agents table exists without the metadata column (e.g. created by an older migration).
Idempotent: adds column only if it does not exist.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_agents_metadata"
down_revision: str | None = "001_unified"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agents' AND column_name = 'metadata'
            ) THEN
                ALTER TABLE agents ADD COLUMN metadata JSONB;
                UPDATE agents SET metadata = '{"status": {"indexing": "completed"}}'::jsonb WHERE metadata IS NULL;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'agents' AND column_name = 'metadata'
            ) THEN
                ALTER TABLE agents DROP COLUMN metadata;
            END IF;
        END $$
    """)
