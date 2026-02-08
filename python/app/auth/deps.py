"""FastAPI dependency: get current user from cookie or Bearer API token."""

from fastapi import Header, HTTPException, Request, status

from app.auth.db import get_session_user_id, get_user_by_id, get_user_id_by_api_token
from app.auth.utils import hash_api_token
from app.config import get_settings


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None, include_in_schema=False),
) -> dict:
    """Load current user from session cookie or Authorization: Bearer <api_token>. Raises 401 if not authenticated."""
    user_id = None
    cookie = request.cookies.get(get_settings().cookie_name)
    if cookie and cookie.strip():
        user_id = get_session_user_id(cookie.strip())
    if user_id is None and authorization and authorization.strip().lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            token_hash = hash_api_token(token)
            user_id = get_user_id_by_api_token(token_hash)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_current_user_id(current_user: dict) -> str:
    """Convenience: return current user id from dependency result."""
    return current_user["id"]
