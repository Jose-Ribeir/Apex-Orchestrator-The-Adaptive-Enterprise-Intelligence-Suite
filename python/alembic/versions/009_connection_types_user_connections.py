"""Connection types and user_connections for OAuth (e.g. Google Gmail).

Revision ID: 009_connection_types
Revises: 008_tokens_duration_quality
Create Date: 2026-02-09

"""

from collections.abc import Sequence

from alembic import op

revision: str = "009_connection_types"
down_revision: str | None = "008_tokens_duration_quality"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS connection_types (
            id UUID NOT NULL PRIMARY KEY,
            name VARCHAR NOT NULL,
            provider_key VARCHAR NOT NULL UNIQUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_connection_types_provider_key ON connection_types (provider_key)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_connections (
            id UUID NOT NULL PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            connection_type_id UUID NOT NULL REFERENCES connection_types(id) ON DELETE CASCADE,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_user_connections_user_connection_type UNIQUE (user_id, connection_type_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_connections_user_id ON user_connections (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_connections_connection_type_id ON user_connections (connection_type_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_connections")
    op.execute("DROP TABLE IF EXISTS connection_types")
