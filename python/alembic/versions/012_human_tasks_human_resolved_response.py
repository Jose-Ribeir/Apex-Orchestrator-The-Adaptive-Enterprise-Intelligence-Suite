"""Add human_resolved_response to human_tasks.

Revision ID: 012_human_resolved_response
Revises: 011_connection_google_gmail
Create Date: 2026-02-11

"""

from collections.abc import Sequence

from alembic import op

revision: str = "012_human_resolved_response"
down_revision: str | None = "011_connection_google_gmail"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE human_tasks ADD COLUMN IF NOT EXISTS human_resolved_response TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE human_tasks DROP COLUMN IF EXISTS human_resolved_response")
