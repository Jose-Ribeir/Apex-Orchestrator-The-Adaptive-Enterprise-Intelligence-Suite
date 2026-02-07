"""Request body schemas for API endpoints."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class CreateAgentRequest(BaseModel):
    """Request to create an agent (stored in DB; Node can pass agent_id to keep same id)."""

    agent_id: str | None = Field(None, description="Optional UUID; if omitted a new one is generated")
    user_id: str = Field(..., description="Owner user id (from auth)")
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


class AgentConfig(BaseModel):
    """Agent configuration for prompt optimization and GeminiMesh updates."""

    agent_id: str = Field(..., description="Agent ID used by GeminiMesh for updates")
    name: str = Field(..., description="Display name of the agent")
    mode: str = Field(default="PERFORMANCE", description="Agent mode (e.g. PERFORMANCE)")
    instructions: list[str] = Field(..., description="List of instruction lines")
    tools: list[str] = Field(default_factory=list, description="Tool names (e.g. RAG, Calculator)")


class ChatRequest(BaseModel):
    """Request for streaming chat with 2-call router + generator."""

    agent_name: str = Field(..., description="Agent name (used for RAG namespace)")
    message: str = Field(..., description="User message")
    system_prompt: str = Field(..., description="Full system prompt including TOOLS line")


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
