"""Auth-related Pydantic schemas (session/user shape for frontend)."""

from pydantic import BaseModel


class UserRead(BaseModel):
    """User as returned to frontend (e.g. GET /users/me)."""

    id: str
    email: str
    name: str
    image: str | None = None
    email_verified: bool = False

    model_config = {"from_attributes": True}


def user_to_read(user: dict) -> UserRead:
    """Build UserRead from DB user dict."""
    return UserRead(
        id=user["id"],
        email=user["email"],
        name=user.get("name") or "",
        image=user.get("image"),
        email_verified=user.get("emailVerified", False),
    )
