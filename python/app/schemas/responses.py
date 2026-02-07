"""Response schemas for API endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    """Single agent in list: agent_id, name, RAG document count; optional user_id when from DB."""

    agent_id: str = Field(..., description="Agent ID (UUID)")
    name: str = Field(..., description="Display name")
    doc_count: int = Field(..., description="Number of documents in this agent's RAG index")
    user_id: str | None = Field(None, description="Owner (when from DB)")


class AgentDetailResponse(BaseModel):
    """Single agent full detail (GET /agents/{id})."""

    agent_id: str = Field(..., description="Agent ID (UUID)")
    user_id: str = Field(..., description="Owner user id")
    name: str = Field(..., description="Display name")
    mode: str = Field(..., description="PERFORMANCE | EFFICIENCY | BALANCED")
    prompt: str | None = Field(None, description="System prompt")
    instructions: list[str] = Field(..., description="Instruction lines in order")
    tools: list[str] = Field(..., description="Tool names")
    doc_count: int = Field(..., description="RAG document count for this agent")


class ListAgentsResponse(BaseModel):
    """Response for GET /agents: all known agents with doc counts."""

    agents: list[AgentInfo] = Field(..., description="Agents that have RAG data (from DATA_FOLDER)")


class CreateAgentResponse(BaseModel):
    """Response after creating an agent."""

    agent_id: str = Field(..., description="Agent ID (UUID)")
    message: str = Field(default="created", description="Human-readable status")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Always 'healthy' when endpoint succeeds")
    agents: list[str] = Field(..., description="List of agent names with loaded RAG")
    geminimesh_configured: bool = Field(..., description="Whether GeminiMesh API token is set")
    embedding_model: str = Field(..., description="'loaded' or 'not_loaded'")
    database_configured: bool = Field(..., description="Whether DATABASE_URL is set")
    database_connected: bool = Field(..., description="Whether DB connection succeeds")


class OptimizePromptResponse(BaseModel):
    """Response from standalone prompt optimization (no GeminiMesh call)."""

    optimized_prompt: str = Field(..., description="Generated system prompt")
    analysis: dict[str, Any] = Field(..., description="Agent type, complexity, needs_rag")
    model_used: str = Field(..., description="Model used for optimization")


class UpdateAgentGeminimeshResponse(BaseModel):
    """Response after updating agent prompt in GeminiMesh."""

    status: str = Field(..., description="'success' on success")
    agent_id: str = Field(..., description="Agent ID that was updated")
    geminimesh_response: dict[str, Any] = Field(..., description="Raw response from GeminiMesh API")
    optimized_prompt: str = Field(..., description="Generated prompt that was sent")
    local_rag_docs: int = Field(..., description="Document count in local RAG for this agent")
    message: str = Field(..., description="Human-readable success message")


class UpdateAgentIndexResponse(BaseModel):
    """Response after updating agent RAG index (add/update/delete)."""

    status: str = Field(..., description="'success' on success")
    total_docs: int = Field(..., description="Total documents in agent index after update")


class UploadAndIndexResponse(BaseModel):
    """Response after uploading a JSONL file and indexing documents."""

    status: str = Field(..., description="'success' on success")
    docs_added: int = Field(..., description="Number of documents parsed and added")
    total_docs: int = Field(..., description="Total documents in agent index after upload")
