"""Add total_tokens, duration_ms, quality_score to model_queries for stats.

Revision ID: 008_tokens_duration_quality
Revises: 007_flow_log
Create Date: 2026-02-09

Enables agent daily stats to show totalTokens, avgEfficiency (latency ms), avgQuality.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "008_tokens_duration_quality"
down_revision: str | None = "007_flow_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE model_queries
        ADD COLUMN IF NOT EXISTS total_tokens INTEGER NULL,
        ADD COLUMN IF NOT EXISTS duration_ms INTEGER NULL,
        ADD COLUMN IF NOT EXISTS quality_score NUMERIC(3,2) NULL
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE model_queries
        DROP COLUMN IF EXISTS total_tokens,
        DROP COLUMN IF EXISTS duration_ms,
        DROP COLUMN IF EXISTS quality_score
    """)
