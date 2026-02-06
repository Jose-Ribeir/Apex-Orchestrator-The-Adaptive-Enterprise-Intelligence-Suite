"""Request body schemas for API endpoints."""

from typing import Any

from pydantic import BaseModel, Field


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

    agent_name: str = Field(..., description="Agent name whose index to update")
    action: str = Field(..., description="One of: add, update, delete")
    doc_id: str | None = Field(None, description="Document ID (required for delete)")
    content: str | None = Field(None, description="JSON string with id, content, optional metadata")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata override")
