"""Rename connection type google to google_gmail and add description for AI context.

Revision ID: 011_connection_google_gmail
Revises: 010_agent_documents_source
Create Date: 2026-02-11

"""

from collections.abc import Sequence

from alembic import op

revision: str = "011_connection_google_gmail"
down_revision: str | None = "010_agent_documents_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Escaped for use in SQL single-quoted string
GMAIL_DESCRIPTION_SQL = (
    "List emails, search emails, find emails, send and reply to emails. "
    "Use when the user asks about their inbox, to find or search messages, or to send/reply to email."
).replace("'", "''")


def upgrade() -> None:
    op.execute("ALTER TABLE connection_types ADD COLUMN IF NOT EXISTS description TEXT")
    # If both 'google' and 'google_gmail' exist, reassign user_connections from google to google_gmail, then drop google row
    op.execute("""
        UPDATE user_connections uc
        SET connection_type_id = (SELECT id FROM connection_types WHERE provider_key = 'google_gmail' LIMIT 1)
        WHERE uc.connection_type_id = (SELECT id FROM connection_types WHERE provider_key = 'google' LIMIT 1)
        AND EXISTS (SELECT 1 FROM connection_types WHERE provider_key = 'google_gmail')
        AND EXISTS (SELECT 1 FROM connection_types WHERE provider_key = 'google')
    """)
    op.execute("DELETE FROM connection_types WHERE provider_key = 'google'")
    # Now at most one row is google_gmail; rename any remaining google to google_gmail and set description
    op.execute(
        f"UPDATE connection_types SET provider_key = 'google_gmail', description = '{GMAIL_DESCRIPTION_SQL}' WHERE provider_key = 'google'"
    )
    op.execute(
        f"UPDATE connection_types SET description = '{GMAIL_DESCRIPTION_SQL}' WHERE provider_key = 'google_gmail' AND (description IS NULL OR description = '')"
    )


def downgrade() -> None:
    op.execute("UPDATE connection_types SET provider_key = 'google' WHERE provider_key = 'google_gmail'")
    op.execute("ALTER TABLE connection_types DROP COLUMN IF EXISTS description")
