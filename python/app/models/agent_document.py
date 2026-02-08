"""Agent document: metadata for RAG-indexed documents (per-agent)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent


class AgentDocument(Base):
    """
    Metadata for an uploaded file.
    """

    __tablename__ = "agent_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)  # first RAG chunk id (for delete)
    rag_document_ids: Mapped[list | None] = mapped_column(JSONB(), nullable=True)  # all RAG chunk ids (for delete)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text(), nullable=True)  # gs:// URI for signed download URL
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="documents")
