"""Auth routes: login, register, logout, me (cookie-based)."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import DatabaseError

logger = logging.getLogger(__name__)

from app.auth.db import (
    create_session,
    create_user,
    delete_session_by_token,
    get_password_for_user,
    get_user_by_email,
)
from app.auth.deps import get_current_user
from app.auth.schemas import UserRead, user_to_read
from app.auth.utils import hash_password, verify_password
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginBody(BaseModel):
    email: str
    password: str


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str = ""


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.cookie_max_age_seconds
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=False,  # set True in prod with HTTPS
        samesite=settings.cookie_same_site,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=get_settings().cookie_name, path="/")


@router.post(
    "/login",
    summary="Login",
    description="Login with email/password; sets session cookie.",
    operation_id="login",
)
async def login(body: LoginBody, response: Response):
    try:
        user = get_user_by_email(body.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        hashed = get_password_for_user(user["id"])
        if not hashed or not verify_password(body.password, hashed):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(seconds=get_settings().cookie_max_age_seconds)
        create_session(user["id"], token, expires.isoformat())
        _set_session_cookie(response, token)
        return {"user": user_to_read(user)}
    except HTTPException:
        raise
    except (RuntimeError, DatabaseError) as e:
        logger.exception("Login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service temporarily unavailable. Check DATABASE_URL and that migrations are applied (alembic upgrade head).",
        ) from e
    except Exception as e:
        logger.exception("Login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. See server logs for details.",
        ) from e


@router.post(
    "/register",
    summary="Register",
    description="Register a new user and set session cookie.",
    operation_id="register",
)
async def register(body: RegisterBody, response: Response):
    try:
        if get_user_by_email(body.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        name = (body.name or body.email.split("@")[0]).strip() or "User"
        hashed = hash_password(body.password)
        user = create_user(email=body.email, name=name, hashed_password=hashed)
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(seconds=get_settings().cookie_max_age_seconds)
        create_session(user["id"], token, expires.isoformat())
        _set_session_cookie(response, token)
        return {"user": user_to_read(user)}
    except HTTPException:
        raise
    except (RuntimeError, DatabaseError) as e:
        logger.exception("Register failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service temporarily unavailable. Check DATABASE_URL and that migrations are applied (alembic upgrade head).",
        ) from e
    except Exception as e:
        logger.exception("Register failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. See server logs for details.",
        ) from e


@router.post(
    "/logout",
    summary="Logout",
    description="Clear session and cookie.",
    operation_id="logout",
)
async def logout(request: Request, response: Response):
    cookie = request.cookies.get(get_settings().cookie_name)
    if cookie:
        delete_session_by_token(cookie)
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Current user",
    description="Return current user (requires cookie or Bearer).",
    operation_id="getAuthMe",
)
async def me(current_user: dict = Depends(get_current_user)):
    return user_to_read(current_user)
