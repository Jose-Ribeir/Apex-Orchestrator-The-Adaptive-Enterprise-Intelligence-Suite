"""Request body schemas for API endpoints."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class CreateAgentRequest(BaseModel):
    """Request to create an agent (stored in DB). Agent ID is always server-generated."""

    user_id: str | None = Field(None, description="Owner user id (from auth; optional when under /api)")
    name: str = Field(..., description="Display name")
    mode: str = Field(default="EFFICIENCY", description="PERFORMANCE | EFFICIENCY | BALANCED")
    prompt: str | None = Field(None, description="System prompt")
    instructions: list[str] = Field(default_factory=list, description="Instruction lines")
    tools: list[str] = Field(default_factory=list, description="Tool names (e.g. RAG, Calculator)")


class UpdateAgentRequest(BaseModel):
    """Request to update an agent (partial)."""

    name: str | None = None
    mode: str | None = None
    prompt: str | None = None
    instructions: list[str] | None = None
    tools: list[str] | None = None
    long_context_mode: bool | None = None
    long_context_max_tokens: int | None = None


class AgentConfig(BaseModel):
    """Agent configuration for prompt optimization and GeminiMesh updates."""

    agent_id: str = Field(..., description="Agent ID used by GeminiMesh for updates")
    name: str = Field(..., description="Display name of the agent")
    mode: str = Field(default="PERFORMANCE", description="Agent mode (e.g. PERFORMANCE)")
    instructions: list[str] = Field(..., description="List of instruction lines")
    tools: list[str] = Field(default_factory=list, description="Tool names (e.g. RAG, Calculator)")


class ChatAttachment(BaseModel):
    """Single attachment: base64-encoded image or audio for multimodal chat."""

    mime_type: str = Field(..., description="IANA MIME type, e.g. image/png, audio/wav")
    data_base64: str = Field(..., description="Base64-encoded bytes (no data URL prefix)")


class ChatRequest(BaseModel):
    """Request for streaming chat with 2-call router + generator.
    When agent_id is set, backend loads agent and builds system_prompt; agent_name and system_prompt are optional.
    When agent_id is not set (legacy), agent_name and system_prompt are required."""

    agent_id: str | None = Field(
        None, description="Agent ID (UUID); when set, backend loads agent and builds system_prompt"
    )
    agent_name: str | None = Field(None, description="Agent name (legacy; required when agent_id is not provided)")
    message: str = Field(..., description="User message")
    system_prompt: str | None = Field(
        None, description="Full system prompt including TOOLS line (legacy; required when agent_id is not provided)"
    )
    attachments: list[ChatAttachment] | None = Field(
        None, description="Optional images or audio as base64 for multimodal chat"
    )

    @model_validator(mode="after")
    def require_agent_id_or_legacy_fields(self) -> "ChatRequest":
        has_id = bool(self.agent_id and str(self.agent_id).strip())
        has_name = bool(self.agent_name and str(self.agent_name).strip())
        has_prompt = bool(self.system_prompt is not None and str(self.system_prompt).strip())
        if has_id:
            return self
        if not has_name or not has_prompt:
            raise ValueError(
                "When agent_id is not provided, both agent_name and system_prompt are required (legacy mode)."
            )
        return self


class UpdateAgentIndexRequest(BaseModel):
    """Request to add, update, or delete a document in an agent's RAG index."""

    agent_id: str | None = Field(None, description="Agent ID (UUID from app API); use this or agent_name")
    agent_name: str | None = Field(None, description="Agent name (legacy); use this or agent_id")
    action: str = Field(..., description="One of: add, update, delete")
    doc_id: str | None = Field(None, description="Document ID (required for delete)")
    content: str | None = Field(None, description="JSON string with id, content, optional metadata")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata override")

    @model_validator(mode="after")
    def require_agent_identifier(self) -> "UpdateAgentIndexRequest":
        has_id = bool(self.agent_id and self.agent_id.strip())
        has_name = bool(self.agent_name and self.agent_name.strip())
        if has_id and has_name:
            raise ValueError("Provide exactly one of agent_id or agent_name")
        if not has_id and not has_name:
            raise ValueError("Provide exactly one of agent_id or agent_name")
        return self

    def agent_key(self) -> str:
        """Resolved key for RAG/GCS (agent_id preferred over agent_name)."""
        return (self.agent_id or self.agent_name or "").strip()
