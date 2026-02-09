"""Add flow_log to model_queries for full request/response flow.

Revision ID: 007_flow_log
Revises: 006_pgvector
Create Date: 2026-02-09

Stores router decision, metrics, and request/response summary for each model query.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "007_flow_log"
down_revision: str | None = "006_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE model_queries
        ADD COLUMN IF NOT EXISTS flow_log JSONB NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE model_queries DROP COLUMN IF EXISTS flow_log")
