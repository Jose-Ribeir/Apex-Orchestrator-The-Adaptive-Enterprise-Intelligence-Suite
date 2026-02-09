"""Connections service: list connection types with status, OAuth start URL, token exchange, disconnect."""

import base64
import hashlib
import hmac
import logging
import secrets
from typing import Any
from uuid import UUID

import requests

from app.config import get_settings
from app.db import session_scope
from app.models import ConnectionType, UserConnection

logger = logging.getLogger("app.connections_service")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _make_state(user_id: str, connection_key: str) -> str:
    nonce = secrets.token_urlsafe(16)
    payload = f"{nonce}:{user_id}:{connection_key}"
    sig = hmac.new(
        get_settings().secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def verify_state(state: str) -> tuple[str, str] | None:
    """Return (user_id, connection_key) if valid, else None."""
    try:
        padded = state + "=" * (4 - len(state) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        parts = raw.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected = hmac.new(
            get_settings().secret_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        # payload = nonce:user_id:connection_key
        _, user_id, connection_key = payload.split(":", 2)
        return (user_id, connection_key)
    except Exception:
        return None


def list_connection_types_with_status(user_id: str) -> list[dict[str, Any]]:
    """List all connection types with connected status and user_connection_id for current user."""
    with session_scope() as session:
        types_rows = session.query(ConnectionType).order_by(ConnectionType.provider_key).all()
        user_conn_map = {
            uc.connection_type_id: uc.id
            for uc in session.query(UserConnection).filter(UserConnection.user_id == user_id).all()
        }
    return [
        {
            "id": str(ct.id),
            "name": ct.name,
            "providerKey": ct.provider_key,
            "connected": ct.id in user_conn_map,
            "userConnectionId": str(user_conn_map[ct.id]) if ct.id in user_conn_map else None,
        }
        for ct in types_rows
    ]


def get_oauth_start_url(connection_provider_key: str, user_id: str, redirect_uri: str) -> str:
    """Build Google OAuth authorization URL. redirect_uri must be the backend callback URL."""
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_id.strip():
        raise ValueError("Google OAuth is not configured (GOOGLE_OAUTH_CLIENT_ID)")
    state = _make_state(user_id, connection_provider_key)
    scopes = " ".join(GMAIL_SCOPES)
    params = {
        "client_id": settings.google_oauth_client_id.strip(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    q = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{q}"


def exchange_code_and_store(
    connection_provider_key: str, user_id: str, code: str, state: str, redirect_uri: str
) -> str:
    """
    Verify state, exchange code for tokens, upsert user_connections.
    Returns frontend redirect URL (success or error).
    """
    from datetime import datetime, timedelta, timezone

    settings = get_settings()
    parsed = verify_state(state)
    if not parsed or parsed[0] != user_id or parsed[1] != connection_provider_key:
        logger.warning("Invalid OAuth state or mismatch")
        return f"{settings.app_frontend_url.rstrip('/')}/settings/connections?error=invalid_state"

    with session_scope() as session:
        ct = session.query(ConnectionType).filter(ConnectionType.provider_key == connection_provider_key).first()
        if not ct:
            return f"{settings.app_frontend_url.rstrip('/')}/settings/connections?error=unknown_connection"
        connection_type_id = ct.id

    resp = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id.strip(),
            "client_secret": settings.google_oauth_client_secret.strip(),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.warning("Google token exchange failed: %s %s", resp.status_code, resp.text[:200])
        return f"{settings.app_frontend_url.rstrip('/')}/settings/connections?error=token_exchange_failed"

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in")

    if not access_token:
        return f"{settings.app_frontend_url.rstrip('/')}/settings/connections?error=no_access_token"

    expires_at = None
    if expires_in is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    with session_scope() as session:
        existing = (
            session.query(UserConnection)
            .filter(UserConnection.user_id == user_id, UserConnection.connection_type_id == connection_type_id)
            .first()
        )
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token or existing.refresh_token
            existing.expires_at = expires_at
        else:
            session.add(
                UserConnection(
                    user_id=user_id,
                    connection_type_id=connection_type_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                )
            )

    return f"{settings.app_frontend_url.rstrip('/')}/settings/connections?connected={connection_provider_key}"


def disconnect_user_connection(user_id: str, user_connection_id: UUID) -> bool:
    """Remove user's connection. Returns True if deleted, False if not found or not owned by user."""
    with session_scope() as session:
        uc = (
            session.query(UserConnection)
            .filter(UserConnection.id == user_connection_id, UserConnection.user_id == user_id)
            .first()
        )
        if not uc:
            return False
        session.delete(uc)
    return True
