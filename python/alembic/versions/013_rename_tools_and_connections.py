"""Rename connection and tool display names for better clarity.

Revision ID: 013_rename_tools_connections
Revises: 012_human_resolved_response
Create Date: 2026-02-11

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "013_rename_tools_connections"
down_revision: str | None = "012_human_resolved_response"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (old_name, temp_name, new_name) - use temp to avoid unique constraint
TOOL_RENAMES = [
    ("Chain-of-Thought (CoT)", "__mig013_cot__", "Step-by-Step Reasoning"),
    ("Straight Model", "__mig013_straight__", "Direct Answer"),
    ("human-in-loop", "__mig013_human__", "Human Escalation"),
]


def _rename_tool_iff_needed(conn, old_name: str, temp_name: str, new_name: str) -> None:
    """Rename tool old->new via temp, or merge agent_tools if new already exists."""
    # Find source: old name or temp (in case migration ran partially)
    r = conn.execute(text("SELECT id FROM tools WHERE name = :n AND is_deleted = false"), {"n": old_name})
    src_row = r.fetchone()
    if not src_row:
        r = conn.execute(text("SELECT id FROM tools WHERE name = :n AND is_deleted = false"), {"n": temp_name})
        src_row = r.fetchone()
    if not src_row:
        return  # Nothing to migrate
    src_id = str(src_row[0])
    r = conn.execute(text("SELECT id FROM tools WHERE name = :n AND is_deleted = false"), {"n": new_name})
    new_row = r.fetchone()
    if new_row:
        new_id = str(new_row[0])
        if src_id != new_id:
            conn.execute(text("UPDATE agent_tools SET tool_id = :new WHERE tool_id = :old"), {"new": new_id, "old": src_id})
            conn.execute(text("UPDATE tools SET is_deleted = true, deleted_at = now() WHERE id = :id"), {"id": src_id})
    else:
        conn.execute(text("UPDATE tools SET name = :new WHERE id = :id"), {"new": new_name, "id": src_id})


def upgrade() -> None:
    op.execute("UPDATE connection_types SET name = 'Gmail Integration' WHERE provider_key = 'google_gmail'")
    conn = op.get_bind()
    for old_name, temp_name, new_name in TOOL_RENAMES:
        _rename_tool_iff_needed(conn, old_name, temp_name, new_name)


def downgrade() -> None:
    op.execute("UPDATE connection_types SET name = 'Google Gmail' WHERE provider_key = 'google_gmail'")
    DOWNGRADE_RENAMES = [
        ("Step-by-Step Reasoning", "Chain-of-Thought (CoT)"),
        ("Direct Answer", "Straight Model"),
        ("Human Escalation", "human-in-loop"),
    ]
    conn = op.get_bind()
    for new_name, old_name in DOWNGRADE_RENAMES:
        conn.execute(text("UPDATE tools SET name = :old WHERE name = :new AND is_deleted = false"), {"old": old_name, "new": new_name})
