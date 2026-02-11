"""Connections API: list connection types with status, OAuth start/callback, disconnect (under /api/connections)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.auth.deps import get_current_user
from app.config import get_settings
from app.services import connections_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connections", tags=["Connections"])


@router.get(
    "",
    summary="List connections",
    description="List supported connection types with connected status for current user.",
    operation_id="listConnections",
)
async def list_connections(current_user: dict = Depends(get_current_user)):
    data = connections_service.list_connection_types_with_status(current_user["id"])
    return {"data": data}


@router.get(
    "/oauth/start",
    summary="Start OAuth flow",
    description="Redirect to Google OAuth consent. Requires connection=google_gmail.",
    operation_id="connections_oauth_start",
    include_in_schema=False,
)
async def oauth_start(
    request: Request,
    connection: str = Query(..., alias="connection"),
    current_user: dict = Depends(get_current_user),
):
    if connection != "google_gmail":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only connection=google_gmail is supported",
        )
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/api/connections/oauth/callback"
    logger.info(
        "oauth_start request.base_url=%r base=%r redirect_uri=%r",
        request.base_url,
        base,
        redirect_uri,
    )
    url = connections_service.get_oauth_start_url(connection, current_user["id"], redirect_uri)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/oauth/callback",
    summary="OAuth callback",
    description="Google redirects here. Exchanges code for tokens and redirects to frontend.",
    operation_id="connections_oauth_callback",
    include_in_schema=False,
)
async def oauth_callback(
    request: Request,
    code: str = Query(..., alias="code"),
    state: str = Query(..., alias="state"),
):
    parsed = connections_service.verify_state(state)
    if not parsed:
        frontend_url = get_settings().app_frontend_url.rstrip("/")
        redirect_url = f"{frontend_url}/settings/connections?error=invalid_state"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    user_id, connection_key = parsed
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/api/connections/oauth/callback"
    logger.info(
        "oauth_callback request.base_url=%r base=%r redirect_uri=%r",
        request.base_url,
        base,
        redirect_uri,
    )
    redirect_url = connections_service.exchange_code_and_store(connection_key, user_id, code, state, redirect_uri)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.delete(
    "/user/{user_connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect",
    description="Remove current user's connection.",
    operation_id="disconnectUserConnection",
)
async def disconnect_user_connection(
    user_connection_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    ok = connections_service.disconnect_user_connection(current_user["id"], user_connection_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return None
