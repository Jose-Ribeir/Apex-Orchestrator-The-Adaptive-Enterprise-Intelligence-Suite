"""Placeholder for DBs stamped with 001_init (no-op).

Revision ID: 001_init
Revises:
Create Date: 2026-02-07

Enables alembic upgrade head when the database was created with an older
revision id (001_init). The real schema is applied in 001_unified.
"""

from collections.abc import Sequence

revision: str = "001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
