"""API tokens: create, list, revoke (under /api)."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.services import api_tokens_service

router = APIRouter(prefix="/api-tokens", tags=["API Tokens"])


class CreateApiTokenBody(BaseModel):
    name: str | None = None
    expires_in_days: int | None = None


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create API token",
    description="Create an API token. The plain token is returned only in this response.",
    operation_id="createApiToken",
)
async def create_api_token(
    body: CreateApiTokenBody,
    current_user: dict = Depends(get_current_user),
):
    expires_at = None
    if body.expires_in_days is not None and body.expires_in_days > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
    return api_tokens_service.create_token(
        current_user["id"],
        name=body.name,
        expires_at=expires_at,
    )


@router.get(
    "",
    summary="List API tokens",
    description="List current user's API tokens (token values are never returned).",
    operation_id="listApiTokens",
)
async def list_api_tokens(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    items, total = api_tokens_service.list_tokens(current_user["id"], page=page, limit=limit)
    pages = (total + limit - 1) // limit if total else 0
    return {
        "data": items,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
            "more": page < pages,
        },
    }


@router.delete(
    "/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API token",
    description="Revoke an API token by ID.",
    operation_id="revokeApiToken",
)
async def revoke_api_token(
    token_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    try:
        ok = api_tokens_service.revoke(token_id, current_user["id"])
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API token not found")
