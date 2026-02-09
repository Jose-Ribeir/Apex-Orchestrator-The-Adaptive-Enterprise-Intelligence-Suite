"""Connections service: list connection types with status, OAuth start URL, token exchange, disconnect."""

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
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


def list_connection_provider_keys() -> list[str]:
    """Return provider_key for all connection types (e.g. ['google']). No user context. Returns [] if DB empty or error."""  # noqa: E501
    try:
        with session_scope() as session:
            rows = session.query(ConnectionType.provider_key).order_by(ConnectionType.provider_key).all()
            return [r[0] for r in rows]
    except Exception:
        return []


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


GMAIL_API_BASE = "https://www.googleapis.com/gmail/v1"


def get_valid_access_token(user_id: str, connection_provider_key: str) -> str | None:
    """Return valid access_token for user's connection (refresh if expired). Only google. None if not connected or refresh fails."""  # noqa: E501
    if connection_provider_key != "google":
        return None
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        return None
    with session_scope() as session:
        ct = session.query(ConnectionType).filter(ConnectionType.provider_key == connection_provider_key).first()
        if not ct:
            return None
        uc = (
            session.query(UserConnection)
            .filter(UserConnection.user_id == user_id, UserConnection.connection_type_id == ct.id)
            .first()
        )
        if not uc or not uc.access_token:
            return None
        now = datetime.now(timezone.utc)
        if uc.expires_at and uc.expires_at <= now and uc.refresh_token:
            resp = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_oauth_client_id.strip(),
                    "client_secret": settings.google_oauth_client_secret.strip(),
                    "refresh_token": uc.refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning("Google token refresh failed: %s %s", resp.status_code, resp.text[:200])
                return uc.access_token
            data = resp.json()
            new_token = data.get("access_token")
            expires_in = data.get("expires_in")
            if new_token:
                uc.access_token = new_token
                if expires_in is not None:
                    uc.expires_at = now + timedelta(seconds=int(expires_in))
                return new_token
        return uc.access_token


def fetch_gmail_recent_summary(access_token: str, max_messages: int = 10) -> str:
    """Fetch recent Gmail message summaries for chat context. Returns plain text or 'No recent messages.'"""  # noqa: E501
    headers = {"Authorization": f"Bearer {access_token}"}
    list_url = f"{GMAIL_API_BASE}/users/me/messages?maxResults={max_messages}"
    try:
        r = requests.get(list_url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning("Gmail list messages failed: %s %s", r.status_code, r.text[:200])
            return "[Gmail: unable to list messages.]"
        data = r.json()
        messages = data.get("messages") or []
        if not messages:
            return "No recent messages."
        lines = []
        for i, m in enumerate(messages[:max_messages], 1):
            msg_id = m.get("id")
            if not msg_id:
                continue
            get_url = (
                f"{GMAIL_API_BASE}/users/me/messages/{msg_id}"
                "?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
            )
            mr = requests.get(get_url, headers=headers, timeout=10)
            if mr.status_code != 200:
                lines.append(f"Message {i}: [could not load]")
                continue
            md = mr.json()
            from_h = subj_h = date_h = ""
            for h in md.get("payload", {}).get("headers") or []:
                n = (h.get("name") or "").lower()
                v = h.get("value") or ""
                if n == "from":
                    from_h = v
                elif n == "subject":
                    subj_h = v
                elif n == "date":
                    date_h = v
            snippet = (md.get("snippet") or "").strip()[:200]
            if snippet:
                snippet = " " + snippet
            lines.append(f"Message {i} (id={msg_id}): From: {from_h} | Subject: {subj_h} | Date: {date_h}{snippet}")
        return "\n".join(lines) if lines else "No recent messages."
    except Exception as e:
        logger.warning("Gmail fetch failed: %s", e, exc_info=True)
        return "[Gmail: error fetching messages.]"


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
