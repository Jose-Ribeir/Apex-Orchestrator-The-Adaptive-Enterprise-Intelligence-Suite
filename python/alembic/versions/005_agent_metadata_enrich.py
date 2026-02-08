"""Backfill agents.metadata.status.enrich to 'pending' where missing.

Revision ID: 005_enrich
Revises: 004_storage_path
Create Date: 2026-02-07

So existing agents have status.enrich in metadata; readers default missing to 'pending' anyway.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "005_enrich"
down_revision: str | None = "004_storage_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        UPDATE agents
        SET metadata = jsonb_set(
            COALESCE(metadata, '{}'::jsonb),
            '{status,enrich}',
            '"pending"'::jsonb,
            true
        )
        WHERE metadata IS NULL
           OR metadata->'status'->'enrich' IS NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE agents
        SET metadata = jsonb_set(
            metadata,
            '{status}',
            COALESCE(metadata->'status', '{}'::jsonb) - 'enrich' - 'enrich_error'
        )
        WHERE metadata->'status'->'enrich' IS NOT NULL
    """)
