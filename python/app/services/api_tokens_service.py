"""API tokens: create, list, revoke."""

import uuid
from datetime import datetime

from sqlalchemy import text

from app.auth.utils import generate_api_token, hash_api_token
from app.db import session_scope


def create_token(
    user_id: str,
    *,
    name: str | None = None,
    expires_at: datetime | None = None,
) -> dict:
    """Create API token. Returns { token, id, name, expires_at } - plain token only in this response."""
    plain = generate_api_token()
    token_hash = hash_api_token(plain)
    token_id = uuid.uuid4()
    with session_scope() as session:
        session.execute(
            text(
                "INSERT INTO api_tokens (id, user_id, token_hash, name, expires_at, created_at, updated_at) "
                "VALUES (:id, :user_id, :token_hash, :name, :expires_at, NOW(), NOW())"
            ),
            {
                "id": token_id,
                "user_id": user_id,
                "token_hash": token_hash,
                "name": (name or "").strip() or None,
                "expires_at": expires_at,
            },
        )
    return {
        "token": plain,
        "id": str(token_id),
        "name": (name or "").strip() or None,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


def list_tokens(user_id: str, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
    """List tokens for user (no token value). Returns (items, total)."""
    offset = (page - 1) * limit
    with session_scope() as session:
        total_row = session.execute(
            text("SELECT COUNT(*) FROM api_tokens WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).fetchone()
        total = total_row[0] if total_row else 0
        rows = session.execute(
            text(
                "SELECT id, name, last_used_at, expires_at, created_at FROM api_tokens "
                "WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"user_id": user_id, "limit": limit, "offset": offset},
        ).fetchall()
    items = [
        {
            "id": str(r[0]),
            "name": r[1],
            "last_used_at": r[2].isoformat() if r[2] else None,
            "expires_at": r[3].isoformat() if r[3] else None,
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]
    return items, total


def revoke(token_id: uuid.UUID, user_id: str) -> bool:
    """Revoke token by id for user. Returns True if deleted."""
    with session_scope() as session:
        result = session.execute(
            text("DELETE FROM api_tokens WHERE id = :id AND user_id = :user_id"),
            {"id": token_id, "user_id": user_id},
        )
        return result.rowcount > 0
