"""Auth DB: user, session, account (existing Better Auth–style tables). Uses sync SQLAlchemy."""

from sqlalchemy import text

from app.db import session_scope


def get_user_by_id(user_id: str) -> dict | None:
    """Load user by id. Returns dict with keys id, name, email, image, emailVerified (bool)."""
    with session_scope() as session:
        row = session.execute(
            text('SELECT id, name, email, image, "emailVerified" FROM "user" WHERE id = :id'),
            {"id": user_id},
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "image": row[3],
        "emailVerified": bool(row[4]) if row[4] is not None else False,
    }


def get_users_by_ids(user_ids: list[str]) -> dict[str, dict]:
    """Load users by ids. Returns map user_id -> { id, name } (only id and name). Empty list returns {}."""
    if not user_ids:
        return {}
    with session_scope() as session:
        # Use a simple IN clause; for very large lists consider batching
        placeholders = ", ".join(f":id_{i}" for i in range(len(user_ids)))
        params = {f"id_{i}": uid for i, uid in enumerate(user_ids)}
        rows = session.execute(
            text(f'SELECT id, name FROM "user" WHERE id IN ({placeholders})'),
            params,
        ).fetchall()
    return {row[0]: {"id": row[0], "name": row[1] or ""} for row in rows}


def get_user_by_email(email: str) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text('SELECT id, name, email, image, "emailVerified" FROM "user" WHERE LOWER(email) = LOWER(:email)'),
            {"email": email},
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "image": row[3],
        "emailVerified": bool(row[4]) if row[4] is not None else False,
    }


def get_password_for_user(user_id: str) -> str | None:
    """Get hashed password from account table (providerId = credential) or user.hashed_password."""
    with session_scope() as session:
        # Prefer user.hashed_password if present (FastAPI Users style)
        row = session.execute(
            text('SELECT hashed_password FROM "user" WHERE id = :id'),
            {"id": user_id},
        ).fetchone()
        if row and row[0]:
            return row[0]
        # Fallback: Better Auth stores in account table
        row = session.execute(
            text('SELECT password FROM "account" WHERE "userId" = :user_id AND "providerId" = \'credential\''),
            {"user_id": user_id},
        ).fetchone()
    return row[0] if row and row[0] else None


def create_user(*, email: str, name: str, hashed_password: str, image: str | None = None) -> dict:
    """Create user and credential account. Returns user dict."""
    import uuid

    uid = str(uuid.uuid4())
    with session_scope() as session:
        session.execute(
            text(
                'INSERT INTO "user" (id, name, email, "emailVerified", image, '
                '"createdAt", "updatedAt", hashed_password, is_active, is_superuser) '
                "VALUES (:id, :name, :email, false, :image, NOW(), NOW(), :hashed_password, true, false)"
            ),
            {
                "id": uid,
                "name": name,
                "email": email,
                "image": image,
                "hashed_password": hashed_password,
            },
        )
        session.execute(
            text(
                'INSERT INTO "account" ("id", "userId", "accountId", "providerId", '
                '"password", "createdAt", "updatedAt") '
                "VALUES (:id, :user_id, :account_id, 'credential', :password, NOW(), NOW())"
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "account_id": uid,
                "password": hashed_password,
            },
        )
    return get_user_by_id(uid) or {"id": uid, "name": name, "email": email, "image": image, "emailVerified": False}


def create_session(user_id: str, token: str, expires_at_iso: str) -> None:
    import uuid

    with session_scope() as session:
        session.execute(
            text(
                'INSERT INTO "session" (id, "userId", token, "expiresAt", "createdAt", "updatedAt") '
                "VALUES (:id, :user_id, :token, CAST(:expires_at AS TIMESTAMPTZ), NOW(), NOW())"
            ),
            {"id": str(uuid.uuid4()), "user_id": user_id, "token": token, "expires_at": expires_at_iso},
        )


def get_session_user_id(token: str) -> str | None:
    """Return user_id if session exists and not expired."""
    with session_scope() as session:
        row = session.execute(
            text('SELECT "userId" FROM "session" WHERE token = :token AND "expiresAt" > NOW()'),
            {"token": token},
        ).fetchone()
    return row[0] if row else None


def delete_session_by_token(token: str) -> None:
    with session_scope() as session:
        session.execute(text('DELETE FROM "session" WHERE token = :token'), {"token": token})


def get_user_id_by_api_token(token_hash: str) -> str | None:
    """Return user_id if token valid; updates last_used_at."""
    with session_scope() as session:
        row = session.execute(
            text("SELECT user_id FROM api_tokens WHERE token_hash = :h AND (expires_at IS NULL OR expires_at > NOW())"),
            {"h": token_hash},
        ).fetchone()
        if not row:
            return None
        user_id = row[0]
        session.execute(
            text("UPDATE api_tokens SET last_used_at = NOW() WHERE token_hash = :h"),
            {"h": token_hash},
        )
    return user_id
