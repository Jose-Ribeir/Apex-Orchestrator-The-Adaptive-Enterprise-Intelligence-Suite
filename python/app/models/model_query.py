"""ModelQuery model: per-agent query log."""
# pyright: ignore[reportUndefinedVariable]

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ModelQuery(Base):
    __tablename__ = "model_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_query: Mapped[str] = mapped_column(Text(), nullable=False)
    model_response: Mapped[str | None] = mapped_column(Text(), nullable=True)
    method_used: Mapped[str] = mapped_column(String(), nullable=False)  # PERFORMANCE, EFFICIENCY
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean(), server_default="false", nullable=False)
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_task: Mapped["HumanTask | None"] = relationship(  # noqa: F821
        "HumanTask", back_populates="model_query", uselist=False, cascade="all, delete-orphan"
    )
