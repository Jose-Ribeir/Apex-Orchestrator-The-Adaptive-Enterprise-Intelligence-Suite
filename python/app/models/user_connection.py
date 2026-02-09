"""UserConnection model: user-linked OAuth credentials per connection type."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

# Register the auth "user" table (created by migrations) so FK("user.id") can resolve.
# No mapper; this app does not use ORM for user/session. quote=True for PostgreSQL reserved name.
user_table = Table(
    "user",
    Base.metadata,
    Column("id", String(), primary_key=True),
    quote=True,
)


class UserConnection(Base):
    __tablename__ = "user_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "connection_type_id", name="uq_user_connections_user_connection_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String(), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connection_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_token: Mapped[str] = mapped_column(Text(), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text(), nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    connection_type: Mapped["ConnectionType"] = relationship(  # noqa: F821
        "ConnectionType", back_populates="user_connections"
    )
