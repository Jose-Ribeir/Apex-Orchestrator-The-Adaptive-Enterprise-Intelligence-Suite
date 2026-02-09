"""Agent model: user-owned agents with instructions and tools."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.agent_document import AgentDocument
from app.models.agent_tool import AgentTool
from app.models.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(), nullable=False)
    mode: Mapped[str] = mapped_column(String(), nullable=False)  # PERFORMANCE, EFFICIENCY, BALANCED
    prompt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean(), server_default="false", nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB(), nullable=True)

    @property
    def resolved_metadata(self) -> dict:
        """Return metadata dict; default status.indexing = 'completed', status.enrich = 'pending' when NULL."""
        if self.metadata_ and isinstance(self.metadata_, dict):
            return self.metadata_
        return {"status": {"indexing": "completed", "enrich": "pending"}}

    instructions: Mapped[list["AgentInstruction"]] = relationship(  # noqa: F821
        "AgentInstruction", back_populates="agent", cascade="all, delete-orphan", order_by="AgentInstruction.order"
    )
    agent_tools: Mapped[list["AgentTool"]] = relationship(  # noqa: F821
        "AgentTool", back_populates="agent", cascade="all, delete-orphan"
    )
    documents: Mapped[list["AgentDocument"]] = relationship(  # noqa: F821
        "AgentDocument", back_populates="agent", cascade="all, delete-orphan"
    )
