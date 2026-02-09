"""ConnectionType model: supported OAuth providers (e.g. Google), seeded."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ConnectionType(Base):
    __tablename__ = "connection_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(), unique=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user_connections: Mapped[list["UserConnection"]] = relationship(  # noqa: F821
        "UserConnection", back_populates="connection_type", cascade="all, delete-orphan"
    )
